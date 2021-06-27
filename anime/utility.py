import datetime
import re
from abc import ABC
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import aiohttp
from redbot.vendored.discord.ext import menus

ANILIST_API_ENDPOINT = "https://graphql.anilist.co"

ANIMETHEMES_BASE_URL = "https://staging.animethemes.moe/api"

ANIMENEWSNETWORK_NEWS_FEED_ENDPOINT = "https://www.animenewsnetwork.com/newsroom/rss.xml"

CRUNCHYROLL_NEWS_FEED_ENDPOINT = "https://www.crunchyroll.com/newsrss?lang=enEN"


class AnimeThemesException(Exception):
    """
    Base exception class for the AnimeThemes API wrapper.
    """


class AnimeThemesAPIError(AnimeThemesException):
    """
    Exception due to an error response from the AnimeThemes API.
    """

    def __init__(self, msg: str, status: int) -> None:
        """
        Initializes the AnimeThemesAPIError exception.
        Args:
            msg (str): The error message.
            status (int): The status code.
        """
        super().__init__(msg + " - Status: " + str(status))


class AnimeThemesError(AnimeThemesException):
    """
    Exceptions that do not involve the API.
    """


class AnimeThemesClient:
    """
    Asynchronous wrapper client for the AnimeThemes API.
    This class is used to interact with the API.
    Attributes:
        session (aiohttp.ClientSession): An aiohttp session.
        headers (dict): HTTP headers used in the request.
    """

    def __init__(
        self, session: Optional[aiohttp.ClientSession] = None, headers: Dict[str, Any] = None
    ) -> None:
        """
        Initializes the AnimeThemesClient.
        Args:
            session (aiohttp.ClientSession, optional): An aiohttp session.
            headers (dict, optional): HTTP headers used in the request.
        """
        self.session = session
        self.headers = headers or {}

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

    async def _request(self, url: str) -> Dict[str, Any]:
        """
        Makes a request to the AnimeThemes API.
        Args:
            url (str): The url used for the request.
        Returns:
            dict: Dictionary with the data from the response.
        Raises:
            AnimeThemesAPIError: If the response contains an error.
        """
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
        """
        Creates the request url for the animethemes endpoints.
        Args:
            endpoint (str): The API endpoint.
            parameters (str): The query parameters.
        """
        return f"{ANIMETHEMES_BASE_URL}/{endpoint}{parameters}"

    async def search(
        self, query: str, limit: Optional[int] = 5, fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Returns relevant resources by search criteria.
        Args:
            query (str): The search query.
            limit (int, optional): The number of each resource to return (1-5).
            fields (str, optional): The list of resources to include.
        Returns:
            dict: The data about the requested resources.
        """
        q = query.replace(" ", "%20")
        if fields is None:
            fields = []
        parameters = f'?q={q}&limit={limit}&fields={",".join(fields)}'
        url = await self.get_url("search", parameters)
        data = await self._request(url=url)
        return data


class HTMLFilter(HTMLParser, ABC):
    """
    A simple no deps HTML -> TEXT converter.
    thanks https://stackoverflow.com/a/55825140
    copy pasted from https://gist.github.com/ye/050e898fbacdede5a6155da5b3db078d
    """

    text = ""

    def handle_data(self, data):
        self.text += data


class AniListSearchType:
    Anime = "Anime"
    Manga = "Manga"
    Character = "Character"
    Staff = "Staff"
    Studio = "Studio"


class AniListMediaType:
    Anime = "Anime"
    Manga = "Manga"


class EmbedListMenu(menus.ListPageSource):
    """
    Paginated embed menu.
    """

    def __init__(self, embeds):
        """
        Initializes the EmbedListMenu.
        """
        super().__init__(embeds, per_page=1)

    async def format_page(self, menu, embeds):
        """
        Formats the page.
        """
        return embeds


def get_media_title(data: Dict[str, Any]) -> str:
    """
    Returns the media title.
    """
    if data.get("english") is None or data.get("english") == data.get("romaji"):
        return data.get("romaji")
    else:
        return "{} ({})".format(data.get("romaji"), data.get("english"))


def get_media_stats(format_: str, type_: str, status: str, mean_score: int) -> str:
    """
    Returns the media stats.
    """
    anime_stats = []
    anime_type = "Type: " + format_media_type(format_) if format_ else "N/A"
    anime_stats.append(anime_type)
    anime_status = "N/A"
    if type_ == "ANIME":
        anime_status = "Status: " + format_anime_status(status)
    elif type_ == "MANGA":
        anime_status = "Status: " + format_manga_status(status)
    anime_stats.append(anime_status)
    anime_score = "Score: " + str(mean_score) if mean_score else "N/A"
    anime_stats.append(anime_score)
    return " | ".join(anime_stats)


def get_char_staff_name(data: Dict[str, Any]) -> str:
    """
    Returns the character/staff name.
    """
    if data.get("full") is None or data.get("full") == data.get("native"):
        name = data.get("native")
    else:
        if data.get("native") is None:
            name = data.get("full")
        else:
            name = "{} ({})".format(data.get("full"), data.get("native"))
    return name


def format_media_type(media_type: str) -> str:
    """Formats the anilist media type."""
    MediaType = {
        "TV": "TV",
        "MOVIE": "Movie",
        "OVA": "OVA",
        "ONA": "ONA",
        "TV_SHORT": "TV Short",
        "MUSIC": "Music",
        "SPECIAL": "Special",
        "ONE_SHOT": "One Shot",
        "NOVEL": "Novel",
        "MANGA": "Manga",
    }
    return MediaType[media_type]


def format_anime_status(media_status: str) -> str:
    """Formats the anilist anime status."""
    AnimeStatus = {
        "FINISHED": "Finished",
        "RELEASING": "Currently Airing",
        "NOT_YET_RELEASED": "Not Yet Aired",
        "CANCELLED": "Cancelled",
    }
    return AnimeStatus[media_status]


def format_manga_status(media_status: str) -> str:
    """Formats the anilist manga status."""
    MangaStatus = {
        "FINISHED": "Finished",
        "RELEASING": "Publishing",
        "NOT_YET_RELEASED": "Not Yet Published",
        "CANCELLED": "Cancelled",
    }
    return MangaStatus[media_status]


def clean_html(raw_text) -> str:
    """Removes the html tags from a text."""
    clean = re.compile("<.*?>")
    clean_text = re.sub(clean, "", raw_text)
    return clean_text


def format_description(description: str, length: int) -> str:
    """Formats the anilist description."""
    description = clean_html(description)
    # Remove markdown
    description = description.replace("**", "").replace("__", "")
    # Replace spoiler tags
    description = description.replace("~!", "||").replace("!~", "||")
    if len(description) > length:
        description = description[0:length]
        spoiler_tag_count = description.count("||")
        if spoiler_tag_count % 2 != 0:
            return description + "...||"
        return description + "..."
    return description


def format_date(day: int, month: int, year: int) -> str:
    """Formats the anilist date."""
    month = datetime.date(1900, month, 1).strftime("%B")
    date = f"{month} {str(day)}, {year}"
    return date


def is_adult(data: Dict[str, Any]) -> bool:
    """
    Checks if the media is intended only for 18+ adult audiences.
    """
    if data.get("isAdult") is True:
        return True
    if data.get("is_adult") is True:
        return True
    return data.get("nsfw") is True
