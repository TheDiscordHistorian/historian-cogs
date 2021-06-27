import logging
from typing import Any, Dict, Optional

import aiohttp

from ..utility import ANIMETHEMES_BASE_URL

log = logging.getLogger("red.historian.anime")


class AnimeThemesException(Exception):
    """Base exception class for the AnimeThemes API wrapper."""


class AnimeThemesAPIError(AnimeThemesException):
    """Exception due to an error response from the AnimeThemes API."""

    def __init__(self, msg: str, status: int) -> None:
        super().__init__(msg + " - Status: " + str(status))


class AnimeThemesClient:
    """Asynchronous wrapper client for the AnimeThemes API."""

    def __init__(
        self, session: Optional[aiohttp.ClientSession] = None, headers: Dict[str, Any] = None
    ) -> None:
        self.session = session
        if headers:
            self.headers = headers
        else:
            self.headers = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Closes the aiohttp session."""
        if self.session is not None:
            await self.session.close()

    async def _session(self) -> aiohttp.ClientSession:
        """Gets an aiohttp session by creating it if it does not already exist or the previous session is closed."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(self, url: str) -> Dict[str, Any]:
        """Makes a request to the AnimeThemes API."""
        session = await self._session()
        response = await session.get(url=url, headers=self.headers)
        data = await response.json()
        if data.get("errors"):
            raise AnimeThemesAPIError(
                data.get("errors")[0]["detail"], data.get("errors")[0]["status"]
            )
        return data

    @staticmethod
    async def get_url(endpoint: str, parameters: str) -> str:
        """Creates the request url for the animethemes endpoints."""
        request_url = f"{ANIMETHEMES_BASE_URL}/{endpoint}{parameters}"
        return request_url

    async def search(self, query: str, limit: Optional[int] = 5) -> Dict[str, Any]:
        """Returns relevant resources by search criteria."""
        q = "%20".join(query.split())
        parameters = (
            f"?q={q}&limit={limit}&fields[search]=anime&include="
            f"themes.entries.videos%2Cthemes.song.artists%2Cimages"
        )
        url = await self.get_url("search", parameters)
        data = await self._request(url=url)
        return data
