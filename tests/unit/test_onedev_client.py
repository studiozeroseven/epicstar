"""Unit tests for the OneDev client (URL builders, payload, behavior)."""

import httpx
import pytest

from app.config import settings
from app.integrations.onedev_client import OneDevClient
from app.services.sync_orchestrator import SyncOrchestrator
from app.utils.exceptions import OneDevAPIError


class TestUrlBuilders:
    def test_api_base_uses_tilde_api(self):
        c = OneDevClient()
        assert c.api_base == f"{settings.onedev_api_url.rstrip('/')}/~api"

    def test_git_url_embeds_user_and_token(self):
        c = OneDevClient()
        url = c.build_git_url("github-octocat-hello-world")
        assert url.startswith("https://")
        assert url.endswith("@test.onedev.example.com/github-octocat-hello-world.git")
        assert "test-user" in url
        assert "test_token" in url

    def test_git_url_percent_encodes_special_characters(self, monkeypatch):
        # user/token values often contain characters illegal in URLs.
        from app.config import settings as s

        monkeypatch.setattr(s, "onedev_username", "user with spaces")
        monkeypatch.setattr(s, "onedev_api_token", "tok/en+&=?")
        url = OneDevClient().build_git_url("p")
        assert "user%20with%20spaces" in url
        assert "tok%2Fen%2B%26%3D%3F" in url
        # The raw unescaped characters must NOT appear.
        assert "user with spaces" not in url

    def test_redact_url_removes_credentials(self):
        c = OneDevClient()
        url = c.build_git_url("github-some-repo")
        redacted = c.redact_url(url)
        assert "@" not in redacted
        assert "test_token" not in redacted
        assert redacted.startswith("https://test.onedev.example.com")

    def test_redact_url_leaves_plain_urls(self):
        assert OneDevClient().redact_url("https://host/path") == "https://host/path"


class TestCreatePayload:
    def test_required_fields_present(self):
        payload = OneDevClient()._create_payload("github-x", "d")
        assert payload["name"] == "github-x"
        assert payload["codeManagement"] is True
        assert payload["issueManagement"] is False
        assert "gitPackConfig" in payload
        assert payload["codeIndexingSetting"] == {"analysisFiles": None}
        assert "parentId" not in payload

    def test_parent_id_included_when_set(self, monkeypatch):
        monkeypatch.setattr(settings, "onedev_project_parent_id", 7)
        payload = OneDevClient()._create_payload("github-x", "d")
        assert payload["parentId"] == 7


class TestResponseParsing:
    @staticmethod
    def _resp(status_code: int, text: str = "", data=None) -> httpx.Response:
        if data is not None:
            return httpx.Response(
                status_code=status_code,
                json=data,
                request=httpx.Request("POST", "https://x/~api/projects"),
            )
        return httpx.Response(
            status_code=status_code,
            text=text,
            request=httpx.Request("POST", "https://x/~api/projects"),
        )

    @staticmethod
    def _no_existing(client_obj):
        """Stub find_project_by_name so tests start at the create call."""

        async def _none(name):
            return None

        client_obj.find_project_by_name = _none

    async def test_create_returns_plain_text_id(self, monkeypatch):
        c = OneDevClient()
        self._no_existing(c)
        responses = [
            self._resp(200, text="555"),
            self._resp(
                200,
                data={"id": 555, "name": "github-x", "path": "github-x"},
            ),
        ]
        calls = []

        async def fake_request(method, path, **kwargs):
            calls.append(path)
            return responses.pop(0)

        monkeypatch.setattr(c, "_request", fake_request)
        result = await c.get_or_create_repository("github-x", "desc")
        assert result["id"] == 555
        assert result["path"] == "github-x"
        assert result["git_url"].startswith("https://")
        assert "/projects" in calls[0]

    async def test_no_json_on_create_response(self, monkeypatch):
        # Old code did response.json() on the plain-text id body - regression guard.
        c = OneDevClient()
        self._no_existing(c)
        monkeypatch.setattr(
            c,
            "_request",
            self._fake_seq(
                self._resp(200, text="123"),
                self._resp(200, data={"id": 123, "name": "n", "path": "n"}),
            ),
        )
        result = await c.get_or_create_repository("n")
        assert result["id"] == 123

    @staticmethod
    def _fake_seq(*responses):
        """A fake _request replacement that consumes responses in order."""
        remaining = list(reversed(responses))

        async def _inner(method, path, **kwargs):
            assert remaining, "no more canned responses"
            return remaining.pop()

        return _inner

    async def test_unrecognized_field_swaps_to_legacy(self, monkeypatch):
        c = OneDevClient()
        self._no_existing(c)
        seen_payloads = []

        async def fake_request(method, path, *, json_body=None):
            seen_payloads.append(dict(json_body))
            if len(seen_payloads) == 1:
                assert "codeIndexingSetting" in json_body
                return self._resp(400, text='Unrecognized field "codeIndexingSetting"')
            assert "codeAnalysisSetting" in seen_payloads[-1]
            assert "codeIndexingSetting" not in seen_payloads[-1]
            return self._resp(200, text="77")

        monkeypatch.setattr(c, "_request", fake_request)
        monkeypatch.setattr(c, "get_project", TestResponseParsing._fake_get_project)
        result = await c.get_or_create_repository("github-x")
        assert result["id"] == 77

    @staticmethod
    async def _fake_get_project(project_id):
        return {"id": project_id, "name": "github-x", "path": "github-x"}

    async def test_create_failure_raises(self, monkeypatch):
        c = OneDevClient()
        self._no_existing(c)

        async def fake_request(method, path, *, json_body=None):
            return self._resp(500, text="boom")

        monkeypatch.setattr(c, "_request", fake_request)
        with pytest.raises(OneDevAPIError):
            await c.get_or_create_repository("github-x")

    async def test_existing_project_adopted(self, monkeypatch):
        c = OneDevClient()
        created = {"calls": 0}

        async def fake_list():
            return [{"id": 9, "name": "github-x", "path": "github-x"}]

        async def req(method, path, *, json_body=None):
            created["calls"] += 1
            return self._resp(500, text="should not be reached")

        monkeypatch.setattr(c, "list_projects", fake_list)
        monkeypatch.setattr(c, "_request", req)
        result = await c.get_or_create_repository("github-x")
        assert result["id"] == 9
        assert created["calls"] == 0  # create never posted


class TestNameGeneration:
    def test_generate_onedev_name(self):
        o = SyncOrchestrator()
        assert o._generate_onedev_name("OctoCat", "Hello.World") == (
            f"{settings.onedev_repo_prefix}octocat-hello-world"
        )
