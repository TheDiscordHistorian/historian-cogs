import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp
from bs4 import BeautifulSoup

from .utils import ANIMENEWSNETWORK_NEWS_FEED_ENDPOINT

log = logging.getLogger("red.historian.anime")


class AnimeNewsNetworkException(Exception):
    """
    Base exception class for the Anime News Network RSS feed parser.
    """


class AnimeNewsNetworkFeedError(AnimeNewsNetworkException):
    """
    Exception due to an error response from the Anime News Network RSS feed.
    """

    def __init__(self, status: int) -> None:
        """
        Initializes the AnimeNewsNetworkFeedError exception.
        Args:
            status (int): The status code.
        """
        super().__init__(status)


class AnimeNewsNetworkClientError(AnimeNewsNetworkException):
    """
    Exceptions that do not involve the RSS feed.
    """


class AnimeNewsNetworkClient:
    """
    Asynchronous parser client for the Anime News Network RSS feed.
    This class is used to interact with the RSS feed.
    Attributes:
        session (aiohttp.ClientSession): An aiohttp session.
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """
        Initializes the AnimeNewsNetworkClient.
        Args:
            session (aiohttp.ClientSession, optional): An aiohttp session.
        """
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Closes the aiohttp session.
        """
        if self.session is not None:
            await self.session.close()

    async def _session(self) -> aiohttp.ClientSession:
        """
        Gets an aiohttp session by creating it if it does not already exist or the previous session is closed.
        Returns:
            aiohttp.ClientSession: An aiohttp session.
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(self, url: str) -> str:
        """
        Makes a request to the Anime News Network RSS feed.
        Args:
            url (str): The url used for the request.
        Returns:
            str: The RSS feed as text.
        Raises:
            AnimeNewsNetworkFeedError: If the response contains an error.
        """
        session = await self._session()
        response = await session.get(url)
        if response.status == 200:
            data = await response.text()
        else:
            raise AnimeNewsNetworkFeedError(response.status)
        return data

    @staticmethod
    async def _parse_feed(text: str, count: int) -> Union[List[Dict[str, Any]], None]:
        """
        Parses the feed and creates a dictionary for each entry.
        Args:
            text (str): The feed as text to parse.
            count (int): The number of items to return.
        Returns:
            list: Dictionaries with the data about the feed.
            None: If no items were found.
        """
        soup = BeautifulSoup(text, "html.parser")
        items = soup.find_all("item")
        if items:
            data = []
            for item in items:
                if len(data) >= count:
                    break
                feed = {
                    "title": item.find("title").text,
                    "link": item.find("guid").text,
                    "description": item.find("description").text,
                    "category": item.find("category").text if item.find("category") else None,
                    "date": item.find("pubdate").text,
                }
                data.append(feed)
            return data
        return None

    async def news(self, count: int) -> Union[List[Dict[str, Any]], None]:
        """
        Gets a list of anime news.
        Args:
            count (int): The number of anime news.
        Returns:
            list: Dictionaries with the data about the anime news.
            None: If no anime news were found.
        """
        text = await self._request(ANIMENEWSNETWORK_NEWS_FEED_ENDPOINT)
        data = await self._parse_feed(text=text, count=count)
        if data:
            return data
        return None
