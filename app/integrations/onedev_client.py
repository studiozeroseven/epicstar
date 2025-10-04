"""OneDev API client."""

from typing import Dict, Optional

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
        self.api_token = settings.onedev_api_token
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        self.timeout = 30.0
        logger.info("OneDev client initialized")

    async def create_repository(
        self, name: str, description: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Create a new repository in OneDev.

        Args:
            name: Repository name
            description: Repository description

        Returns:
            Created repository information

        Raises:
            OneDevAPIError: If API call fails
        """
        url = f"{self.base_url}/api/projects"

        payload = {
            "name": name,
            "description": description or f"Synced from GitHub",
            "codeManagement": True,
            "issueManagement": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout,
                )

                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"Created OneDev repository: {name}")
                    return {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "url": f"{self.base_url}/{name}",
                        "git_url": f"{self.base_url}/{name}.git",
                    }
                elif response.status_code == 409:
                    # Repository already exists
                    if settings.onedev_conflict_strategy == "use_existing":
                        logger.info(f"Repository {name} already exists, using existing")
                        return await self.get_repository(name)
                    else:
                        raise OneDevAPIError(f"Repository {name} already exists")
                else:
                    error_msg = f"Failed to create repository: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise OneDevAPIError(error_msg)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating repository {name}: {e}")
            raise OneDevAPIError(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating repository {name}: {e}")
            raise OneDevAPIError(f"Unexpected error: {e}")

    async def get_repository(self, name: str) -> Dict[str, any]:
        """
        Get repository information.

        Args:
            name: Repository name

        Returns:
            Repository information

        Raises:
            OneDevAPIError: If API call fails
        """
        url = f"{self.base_url}/api/projects/{name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "url": f"{self.base_url}/{name}",
                        "git_url": f"{self.base_url}/{name}.git",
                    }
                else:
                    raise OneDevAPIError(f"Repository not found: {name}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting repository {name}: {e}")
            raise OneDevAPIError(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting repository {name}: {e}")
            raise OneDevAPIError(f"Unexpected error: {e}")

    async def repository_exists(self, name: str) -> bool:
        """
        Check if repository exists.

        Args:
            name: Repository name

        Returns:
            True if exists, False otherwise
        """
        try:
            await self.get_repository(name)
            return True
        except OneDevAPIError:
            return False

    def get_git_url(self, name: str) -> str:
        """
        Get Git URL for repository.

        Args:
            name: Repository name

        Returns:
            Git URL with authentication
        """
        # For HTTPS authentication with token
        return f"https://oauth2:{self.api_token}@{self.base_url.replace('https://', '').replace('http://', '')}/{name}.git"

