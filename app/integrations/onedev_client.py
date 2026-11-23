"""OneDev API client.

OneDev's REST API lives under ``~api`` (NOT ``/api``) of the server root and
authenticates with HTTP basic auth (username + access token). Verified against
OneDev live (see docs/setup/onedev-setup.md for the endpoint-by-endpoint
behavior this implementation encodes).
"""

from typing import Any, Dict, Optional, cast
from urllib.parse import quote, urlparse

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.utils.exceptions import OneDevAPIError

logger = get_logger(__name__)


class OneDevClient:
    """OneDev API client."""

    def __init__(self) -> None:
        """Initialize OneDev client."""
        self.base_url = settings.onedev_api_url.rstrip("/")
        self.api_base = f"{self.base_url}/~api"
        self._auth = (settings.onedev_username, settings.onedev_api_token)
        self.timeout = 60.0

    # ------------------------------------------------------------------ plumbing
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
    ) -> httpx.Response:
        """Perform an authenticated request against the OneDev ~api."""
        url = f"{self.api_base}{path}"
        try:
            async with httpx.AsyncClient() as client:
                return await client.request(
                    method,
                    url,
                    json=json_body,
                    auth=self._auth,
                    timeout=self.timeout,
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as e:
            raise OneDevAPIError(f"OneDev {method} {path} failed: {e}") from e

    # ------------------------------------------------------------------ url helpers
    def redact_url(self, url: str) -> str:
        """Strip userinfo (credentials) from a URL for safe logging."""
        try:
            parts = urlparse(url)
            if parts.username or parts.password:
                netloc = parts.hostname or ""
                if parts.port:
                    netloc = f"{netloc}:{parts.port}"
                rebuilt = parts._replace(netloc=netloc)
                return rebuilt.geturl()
        except ValueError:
            pass
        return url

    def build_git_url(self, project_path: str) -> str:
        """Git clone/push URL with basic-auth credentials embedded.

        OneDev requires ``<username>:<token>`` for git-over-HTTPS; a bare or
        bearer token does not work.
        """
        host = urlparse(self.base_url).netloc
        username = quote(settings.onedev_username, safe="")
        token = quote(settings.onedev_api_token, safe="")
        return f"https://{username}:{token}@{host}/{project_path}.git"

    def build_web_url(self, project_path: str) -> str:
        """Web UI URL for a project given its path."""
        return f"{self.base_url}/{project_path}"

    # ------------------------------------------------------------------ read
    async def get_project(self, project_id: int) -> Optional[dict]:
        """Get one project by numeric id; returns None when absent."""
        response = await self._request("GET", f"/projects/{project_id}")
        if response.status_code == 200:
            return cast(Dict[str, Any], response.json())
        return None

    async def list_projects(self) -> list[dict]:
        """List all projects (paginated; offset+count are mandatory)."""
        projects: list[dict] = []
        offset = 0
        page_size = 100
        for _ in range(1000):  # hard guard against pagination bugs
            response = await self._request(
                "GET",
                f"/projects?offset={offset}&count={page_size}",
            )
            page = response.json()
            if not isinstance(page, list):
                raise OneDevAPIError("Unexpected OneDev project list response")
            projects.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return projects

    async def find_project_by_name(self, name: str) -> Optional[dict]:
        """Find a project by its name (top-level path segment match)."""
        for project in await self.list_projects():
            path = project.get("path") or project.get("name") or ""
            segments = path.rsplit("/", 1)
            if name in (segments[-1], project.get("name")):
                return project
        return None

    # ------------------------------------------------------------------ write
    def _create_payload(self, name: str, description: str) -> dict:
        """Build the createProject payload OneDev accepts.

        ``gitPackConfig`` and the code-indexing block are REQUIRED - omitting
        either yields HTTP 400/406 with a field-validation error. OneDev
        versions differ on the later field's name (codeIndexingSetting in
        recent releases, codeAnalysisSetting in older ones); the create call
        retries the legacy spelling when the server rejects the modern one.
        """
        payload: dict = {
            "name": name,
            "key": name,
            "description": description,
            "codeManagement": True,
            "packManagement": False,
            "issueManagement": False,
            "timeTracking": False,
            "serviceDeskEmailAddress": None,
            "gitPackConfig": {
                "windowMemory": None,
                "packSizeLimit": None,
                "threads": None,
                "window": None,
            },
            "codeIndexingSetting": {"analysisFiles": None},
        }
        if settings.onedev_project_parent_id is not None:
            payload["parentId"] = settings.onedev_project_parent_id
        return payload

    async def _post_create(self, name: str, description: str) -> int:
        """POST the create payload; returns the new numeric project id.

        The create endpoint returns the id as plain text (not JSON). OneDev
        versions disagree on the required code-indexing field's name; when the
        server rejects it, retry once with the other spelling.
        """
        payload = self._create_payload(name, description)
        response = await self._request("POST", "/projects", json_body=payload)
        if response.status_code in (200, 201):
            body = (response.text or "").strip()
            try:
                return int(body)
            except ValueError:
                raise OneDevAPIError(
                    "OneDev project creation returned an unexpected body: " f"{body[:200]!r}"
                )

        text = (response.text or "").strip()
        if response.status_code in (400, 406) and "Unrecognized field" in text:
            # Version adaptation: swap the code-indexing field name once.
            field = next(f for f in ("codeIndexingSetting", "codeAnalysisSetting") if f in payload)
            alt = "codeAnalysisSetting" if field == "codeIndexingSetting" else "codeIndexingSetting"
            payload.pop(field)
            payload[alt] = {"analysisFiles": None}
            response = await self._request("POST", "/projects", json_body=payload)
            if response.status_code in (200, 201):
                return int((response.text or "").strip())
            text = (response.text or "").strip()

        if "already exist" in text.lower():
            raise OneDevAPIError(f"OneDev project '{name}' already exists: {text[:200]}")
        logger.error(
            "Failed to create OneDev project '%s': HTTP %s %s",
            name,
            response.status_code,
            text[:300],
        )
        raise OneDevAPIError(
            f"Failed to create OneDev project '{name}': "
            f"HTTP {response.status_code} - {text[:300]}"
        )

    async def get_or_create_repository(
        self, name: str, description: Optional[str] = None
    ) -> Dict[str, object]:
        """Idempotently ensure a OneDev project exists; return its details.

        Returns dict with keys: id, name, path, web_url, git_url (git_url
        embeds credentials - redact before logging).
        """
        description = description or "Synced from GitHub"

        existing = await self.find_project_by_name(name)
        if existing:
            logger.info("OneDev project '%s' already exists, using existing", name)
            return self._project_result(existing)

        try:
            project_id = await self._post_create(name, description)
        except OneDevAPIError as e:
            # Duplicate-project race: OneDev reports the conflict with an
            # "already exists" message; adopt the existing project instead.
            if "already exist" in str(e).lower():
                if settings.onedev_conflict_strategy == "fail":
                    raise
                existing = await self.find_project_by_name(name)
                if existing:
                    return self._project_result(existing)
            raise

        project = await self.get_project(project_id)
        if project is None:
            raise OneDevAPIError(
                f"OneDev project '{name}' was created (id {project_id}) "
                "but could not be read back"
            )
        logger.info("Created OneDev project: %s", project.get("path") or name)
        return self._project_result(project)

    def _project_result(self, project: dict) -> Dict[str, object]:
        path = project.get("path") or project.get("name") or ""
        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "path": path,
            "web_url": self.build_web_url(path),
            "git_url": self.build_git_url(path),
        }
