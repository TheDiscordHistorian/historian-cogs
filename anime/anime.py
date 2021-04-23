import datetime
import logging
import random
from typing import Any, Dict, List, Optional, Union

import aiohttp
import discord
from discord import Embed
from redbot.core import commands
from redbot.core.commands import Context
from redbot.vendored.discord.ext import menus

from .anilist import AniListClient
from .animenewsnetwork import AnimeNewsNetworkClient
from .crunchyroll import CrunchyrollClient
from .utils import (AniListMediaType, AniListSearchType, AnimeThemesClient,
                    EmbedListMenu, HTMLFilter, format_anime_status,
                    format_date, format_description, format_manga_status,
                    format_media_type, get_char_staff_name, get_media_stats,
                    get_media_title, is_adult)

log = logging.getLogger("red.historian.anime")


class Anime(commands.Cog):
    """Search for anime, manga, characters and users using Anilist"""

    __version__ = "1.3.0"
    __author__ = "The Discord Historian#2420"
    # from https://github.com/flaree/Flare-Cogs/blob/9ba8c884b0f78f5f2fffce9efec1ca6c8ac600ea/joinmessage/joinmessage.py#L49
    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.anilist = AniListClient(session=aiohttp.ClientSession())
        # self.animethemes = AnimeThemesClient(
        #   session=aiohttp.ClientSession(), headers={"User-Agent": "Some Discord Bot"}
        # )
        self.animenewsnetwork = AnimeNewsNetworkClient(session=aiohttp.ClientSession())
        self.crunchyroll = CrunchyrollClient(session=aiohttp.ClientSession())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def anilist_search(
        self, ctx: Context, search: str, type_: AniListSearchType
    ) -> Union[List[Embed], None]:
        """
        Returns a list of Discord embeds with the retrieved anilist data about the searched entry.
        Args:
            ctx (Context): The context in which the command was invoked under.
            search (str): The entry to be searched for.
            type_ (AniListSearchType): The type to be searched for (`ANIME`, `MANGA`, `CHARACTER`, `STAFF`, `STUDIO`).
        Returns:
            list (Embed): A list of discord embeds.
            None: If no entries were found.
        """
        embeds = []
        data = None

        try:
            if type_ == AniListSearchType.ANIME:
                data = await self.anilist.media(
                    search=search, page=1, perPage=15, type=type_.value
                )
            elif type_ == AniListSearchType.MANGA:
                data = await self.anilist.media(
                    search=search, page=1, perPage=15, type=type_.value
                )
            elif type_ == AniListSearchType.CHARACTER:
                data = await self.anilist.character(search=search, page=1, perPage=15)
            elif type_ == AniListSearchType.STAFF:
                data = await self.anilist.staff(search=search, page=1, perPage=15)
            elif type_ == AniListSearchType.STUDIO:
                data = await self.anilist.studio(search=search, page=1, perPage=15)

        except Exception as e:
            log.exception(e)

            embed = discord.Embed(
                title=f"An error occurred while searching for the {type_.value.lower()} `{search}`. Try again.",
                color=discord.Color.random(),
            )
            embeds.append(embed)

            return embeds

        if data is not None:
            for page, entry in enumerate(data):

                embed = None

                try:
                    if type_ == AniListSearchType.ANIME:
                        embed = await self.get_media_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.MANGA:
                        embed = await self.get_media_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.CHARACTER:
                        embed = await self.get_character_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.STAFF:
                        embed = await self.get_staff_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.STUDIO:
                        embed = await self.get_studio_embed(entry, page + 1, len(data))

                    if is_adult(entry):
                        if not ctx.channel.is_nsfw():
                            embed = discord.Embed(
                                title="Error",
                                color=discord.Color.random(),
                                description=f"Adult content. No NSFW channel.",
                            )
                            embed.set_footer(
                                text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                            )

                except Exception as e:
                    log.exception(e)

                    embed = discord.Embed(
                        title="Error",
                        color=discord.Color.random(),
                        description=f"An error occurred while loading the embed for the {type_.value.lower()}.",
                    )
                    embed.set_footer(
                        text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                    )

                embeds.append(embed)

            return embeds
        return None

    async def anilist_random(
        self, ctx: Context, search: str, type_: AniListMediaType, format_in: List[str]
    ) -> Union[Embed, None]:
        """
        Returns a Discord embed with the retrieved anilist data about a random media of a specified genre.
        Args:
            ctx (Context): The context in which the command was invoked under.
            search (str): The media genre to be searched for.
            type_ (AniListMediaType): The media search type (`ANIME`, `MANGA`).
            format_in (list): The media format.
        Returns:
            Embed: A discord embed.
            None: If no entry was found.
        """
        try:

            data = await self.anilist.genre(
                genre=search, page=1, perPage=1, type=type_.value, format_in=format_in
            )

            if (
                data.get("data")["Page"]["media"] is not None
                and len(data.get("data")["Page"]["media"]) > 0
            ):
                page = random.randrange(1, data.get("data")["Page"]["pageInfo"]["lastPage"])
                data = await self.anilist.genre(
                    genre=search,
                    page=page,
                    perPage=1,
                    type=type_.value,
                    format_in=format_in,
                )

            else:

                data = await self.anilist.tag(
                    tag=search, page=1, perPage=1, type=type_.value, format_in=format_in
                )

                if (
                    data.get("data")["Page"]["media"] is not None
                    and len(data.get("data")["Page"]["media"]) > 0
                ):
                    page = random.randrange(1, data.get("data")["Page"]["pageInfo"]["lastPage"])
                    data = await self.anilist.tag(
                        tag=search,
                        page=page,
                        perPage=1,
                        type=type_.value,
                        format_in=format_in,
                    )
                else:
                    return None

        except Exception as e:
            log.exception(e)

            embed = discord.Embed(
                title=f"An error occurred while searching for a {type_.value.lower()} with the genre `{search}`.",
                color=discord.Color.random(),
            )

            return embed

        if (
            data.get("data")["Page"]["media"] is not None
            and len(data.get("data")["Page"]["media"]) > 0
        ):

            try:
                embed = await self.get_media_embed(data.get("data")["Page"]["media"][0])

                if is_adult(data.get("data")["Page"]["media"][0]):
                    if not ctx.channel.is_nsfw():
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.random(),
                            description=f"Adult content. No NSFW channel.",
                        )

            except Exception as e:
                log.exception(e)

                embed = discord.Embed(
                    title=f"An error occurred while searching for a {type_.value.lower()} with the genre `{search}`.",
                    color=discord.Color.random(),
                )

            return embed

        return None

    @staticmethod
    async def get_media_embed(
        data: Dict[str, Any], page: Optional[int] = None, pages: Optional[int] = None
    ) -> Embed:
        """
        Returns the `media` embed.
        Args:
            data (dict): The data about the anime.
            page (int, optional): The current page.
            pages (page, optional): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        embed = discord.Embed(
            description=format_description(data.get("description"), 400)
            if data.get("description")
            else "N/A",
            colour=int("0x" + data.get("coverImage")["color"].replace("#", ""), 0)
            if data.get("coverImage")["color"]
            else discord.Color.random(),
        )

        if (
            data.get("title")["english"] is None
            or data.get("title")["english"] == data.get("title")["romaji"]
        ):
            embed.title = data.get("title")["romaji"]
        else:
            embed.title = f'{data.get("title")["romaji"]} ({data.get("title")["english"]})'

        if data.get("coverImage")["large"]:
            embed.set_thumbnail(url=data.get("coverImage")["large"])

        if data.get("bannerImage"):
            embed.set_image(url=data.get("bannerImage"))

        stats = []
        type_ = f'Type: {format_media_type(data.get("format")) if data.get("format") else "N/A"}'
        stats.append(type_)

        status = "N/A"
        if data.get("type") == "ANIME":
            status = f'Status: {format_anime_status(data.get("status"))}'
        elif data.get("type") == "MANGA":
            status = f'Status: {format_manga_status(data.get("status"))}'
        stats.append(status)

        score = f'Score: {str(data.get("meanScore")) if data.get("meanScore") else "N/A"}'
        stats.append(score)

        embed.set_author(name=" | ".join(stats))

        if data.get("type") == "ANIME":
            if data.get("status") == "RELEASING":
                try:
                    if data.get("nextAiringEpisode")["episode"]:
                        aired_episodes = str(data.get("nextAiringEpisode")["episode"] - 1)
                        next_episode_time = "N/A"
                        if data.get("nextAiringEpisode")["timeUntilAiring"]:
                            seconds = data.get("nextAiringEpisode")["timeUntilAiring"]
                            next_episode_time = str(datetime.timedelta(seconds=seconds))
                        embed.add_field(
                            name="Aired Episodes",
                            value=f"{aired_episodes} (Next in {next_episode_time})",
                            inline=True,
                        )
                except TypeError:
                    embed.add_field(
                        name="Episodes",
                        value=data.get("episodes") if data.get("episodes") else "N/A",
                        inline=True,
                    )
            else:
                embed.add_field(
                    name="Episodes",
                    value=data.get("episodes") if data.get("episodes") else "N/A",
                    inline=True,
                )

        elif data.get("type") == "MANGA":
            embed.add_field(
                name="Chapters",
                value=data.get("chapters") if data.get("chapters") else "N/A",
                inline=True,
            )
            embed.add_field(
                name="Volumes",
                value=data.get("volumes") if data.get("volumes") else "N/A",
                inline=True,
            )
            embed.add_field(
                name="Source",
                inline=True,
                value=data.get("source").replace("_", " ").title()
                if data.get("source")
                else "N/A",
            )

        if data.get("startDate")["day"]:
            try:
                start_date = format_date(
                    data.get("startDate")["day"],
                    data.get("startDate")["month"],
                    data.get("startDate")["year"],
                )
                end_date = "?"
                if data.get("endDate")["day"]:
                    end_date = format_date(
                        data.get("endDate")["day"],
                        data.get("endDate")["month"],
                        data.get("endDate")["year"],
                    )
                embed.add_field(
                    name="Aired" if data.get("type") == "ANIME" else "Published",
                    value=f"{start_date} to {end_date}",
                    inline=False,
                )
            except TypeError:
                embed.add_field(
                    name="Aired" if data.get("type") == "ANIME" else "Published",
                    value="N/A",
                    inline=False,
                )
        else:
            embed.add_field(
                name="Aired" if data.get("type") == "ANIME" else "Published",
                value="N/A",
                inline=False,
            )

        if data.get("type") == "ANIME":
            duration = "N/A"
            if data.get("duration"):
                duration = str(data.get("duration")) + " {}".format(
                    "min" if data.get("episodes") == 1 else "min each"
                )
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(
                name="Source",
                value=data.get("source").replace("_", " ").title()
                if data.get("source")
                else "N/A",
                inline=True,
            )
            embed.add_field(
                name="Studio",
                value=data.get("studios")["nodes"][0]["name"]
                if data.get("studios")["nodes"]
                else "N/A",
                inline=True,
            )

        if data.get("synonyms"):
            embed.add_field(
                name="Synonyms",
                value=", ".join([f"`{s}`" for s in data.get("synonyms")]),
                inline=False,
            )

        embed.add_field(
            name="Genres",
            inline=False,
            value=", ".join(
                [f"`{g}`" for g in data.get("genres")] if data.get("genres") else "N/A"
            ),
        )

        sites = []
        if data.get("trailer"):
            if data.get("trailer")["site"] == "youtube":
                sites.append(
                    f'[Trailer](https://www.youtube.com/watch?v={data.get("trailer")["id"]})'
                )
        if data.get("externalLinks"):
            for i in data.get("externalLinks"):
                sites.append(f'[{i["site"]}]({i["url"]})')
        embed.add_field(
            name="Streaming and external sites"
            if data.get("type") == "ANIME"
            else "External sites",
            value=" | ".join(sites) if len(sites) > 0 else "N/A",
            inline=False,
        )

        sites = []
        if data.get("siteUrl"):
            sites.append(f'[Anilist]({data.get("siteUrl")})')
            embed.url = data.get("siteUrl")
        if data.get("idMal"):
            sites.append(f'[MyAnimeList](https://myanimelist.net/anime/{str(data.get("idMal"))})')
        embed.add_field(
            name="Find out more",
            value=" | ".join(sites) if len(sites) > 0 else "N/A",
            inline=False,
        )

        if page is not None and pages is not None:
            embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")
        else:
            embed.set_footer(text=f"Provided by https://anilist.co/")

        return embed

    @staticmethod
    async def get_character_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `character` embed.
        Args:
            data (dict): The data about the character.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        embed = discord.Embed(
            color=discord.Color.random(),
            description=format_description(data.get("description"), 1000)
            if data.get("description")
            else "N/A",
        )

        if (
            data.get("name")["full"] is None
            or data.get("name")["full"] == data.get("name")["native"]
        ):
            embed.title = data.get("name")["native"]
        elif data.get("name")["native"] is None:
            embed.title = data.get("name")["full"]
        else:
            embed.title = f'{data.get("name")["full"]} ({data.get("name")["native"]})'

        embed.set_author(name="Character")

        if data.get("image")["large"]:
            embed.set_thumbnail(url=data.get("image")["large"])

        if data.get("siteUrl"):
            embed.url = data.get("siteUrl")

        if data.get("name")["alternative"] != [""]:
            embed.add_field(
                name="Synonyms",
                inline=False,
                value=", ".join([f"`{a}`" for a in data.get("name")["alternative"]]),
            )

        if data.get("media")["nodes"]:
            media = []
            for x in data.get("media")["nodes"]:
                media.append(f'[{[x][0]["title"]["romaji"]}]({[x][0]["siteUrl"]})')

            if len(media) > 5:
                media = media[0:5]
                media[4] = media[4] + "..."

            embed.add_field(name="Appearances", value=" | ".join(media), inline=False)

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_staff_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `staff` embed.
        Args:
            data (dict): The data about the staff.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        embed = discord.Embed(
            color=discord.Color.random(),
            description=format_description(data.get("description"), 1000)
            if data.get("description")
            else "N/A",
        )

        if (
            data.get("name")["full"] is None
            or data.get("name")["full"] == data.get("name")["native"]
        ):
            embed.title = data.get("name")["native"]
        elif data.get("name")["native"] is None:
            embed.title = data.get("name")["full"]
        else:
            embed.title = f'{data.get("name")["full"]} ({data.get("name")["native"]})'

        embed.set_author(name="Staff")

        if data.get("image")["large"]:
            embed.set_thumbnail(url=data.get("image")["large"])

        if data.get("siteUrl"):
            embed.url = data.get("siteUrl")

        if data.get("staffMedia")["nodes"]:
            staff_roles = []
            for x in data.get("staffMedia")["nodes"]:
                staff_roles.append(f'[{[x][0]["title"]["romaji"]}]({[x][0]["siteUrl"]})')

            if len(staff_roles) > 5:
                staff_roles = staff_roles[0:5]
                staff_roles[4] += "..."

            embed.add_field(name="Staff Roles", value=" | ".join(staff_roles), inline=False)

        if data.get("characters")["nodes"]:
            character_roles = []
            for x in data.get("characters")["nodes"]:
                character_roles.append(f'[{[x][0]["name"]["full"]}]({[x][0]["siteUrl"]})')

            if len(character_roles) > 5:
                character_roles = character_roles[0:5]
                character_roles[4] += "..."

            embed.add_field(
                name="Character Roles", value=" | ".join(character_roles), inline=False
            )

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_studio_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `studio` embed.
        Args:
            data (dict): The data about the studio.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        embed = discord.Embed(color=discord.Color.random(), title=data.get("name"))

        embed.set_author(name="Studio")

        if data.get("siteUrl"):
            embed.url = data.get("siteUrl")

        if data.get("media")["nodes"]:
            if data.get("media")["nodes"][0]["coverImage"]["large"]:
                embed.set_thumbnail(url=data.get("media")["nodes"][0]["coverImage"]["large"])

        if data.get("isAnimationStudio") is True:
            embed.description = "**Animation Studio**"

        if data.get("media")["nodes"]:
            media, length = [], 0
            for x in data.get("media")["nodes"]:
                studio = (
                    f'[{[x][0]["title"]["romaji"]}]({[x][0]["siteUrl"]}) » Type: '
                    f'**{format_media_type([x][0]["format"]) if [x][0]["format"] else "N/A"}** | Episodes: '
                    f'**{[x][0]["episodes"] if [x][0]["episodes"] else "N/A"}**'
                )
                length += len(studio)
                if length >= 1024:
                    break
                media.append(studio)

            embed.add_field(name="Most Popular Productions", value="\n".join(media), inline=False)

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    # @staticmethod
    # async def get_themes_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
    # """
    # Returns the `themes` embed.
    # Args:
    #     data (dict): The data about the themes.
    #   page (int): The current page.
    # pages (page): The number of all pages.
    # Returns:
    #    Embed: A discord embed.
    # """
    # embed = discord.Embed(color=discord.Color.random(), title=data.get('name'))

    # embed.set_author(name='Themes')

    # if data.get('images'):
    #  embed.set_thumbnail(url=data.get('images')[0]['link'])

    # if data.get('resources'):
    #  embed.description = ' | '.join([f'[{site.get("site")}]({site.get("link")})' for site in
    #                                 data.get('resources')])

    # count = 1
    # for theme in data.get('themes'):
    #   if count >= 15:
    #       embed.add_field(name=theme.get('slug'), value='...', inline=False)
    #        break
    #   count += 1

    #   list_ = ['**Title:** ' + theme.get('song')['title']]

    #    if theme.get('song')['artists']:
    #        list_.append('**Artist:** ' + theme.get('song')['artists'][0]['name'])

    #   link = f'[Link](http://animethemes.moe/video/{theme.get("entries")[0]["videos"][0]["basename"]})'
    #    list_.append(link)

    #    embed.add_field(name=theme.get('slug'), value='\n'.join(list_), inline=False)

    # embed.set_footer(text=f'Provided by https://animethemes.moe/ • Page {page}/{pages}')

    # return embed

    # @staticmethod
    # async def get_theme_embed(anime: Dict[str, Any], data: Dict[str, Any]) -> Embed:
    #   """
    #   Returns the `theme` embed.
    #   Args:
    #       anime (dict): The data about the anime the theme is from.
    #       data (dict): The data about the theme.
    #    Returns:
    #       Embed: A discord embed.
    #   """
    #   embed = discord.Embed(color=discord.Color.random(), title=anime.get("name"))

    #   embed.set_author(name=data.get('slug').replace('OP', 'Opening ').replace('ED', 'Ending '))

    #    if anime.get('images'):
    #        embed.set_thumbnail(url=anime.get("images")[0]["link"])

    #    list_ = []

    #     if anime.get('resources'):
    #         list_.append(' | '.join([f'[{site.get("site")}]({site.get("link")})' for site in
    #                                  anime.get('resources')]) + '\n')

    #        list_.append('**Title:** ' + data.get('song')['title'])

    #     if data.get('song')['artists']:
    #          list_.append('**Artist:** ' + data.get('song')['artists'][0]['name'] if
    #                        len(data.get('song')['artists']) == 1 else
    #                         '**Artists:** ' + ', '.join([a.get("name") for a in data.get('song')['artists']]))

    #      embed.description = '\n'.join(list_) if len(list_) > 0 else 'N/A'

    #      embed.set_footer(text=f'Provided by https://animethemes.moe/')

    #       return embed

    @staticmethod
    async def get_aninews_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `aninews` embed.
        Args:
            data (dict): The data about the anime news.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        f = HTMLFilter()
        f.feed(data.get("description"))
        embed = discord.Embed(
            title=data.get("title"),
            url=data.get("link"),
            color=discord.Color.random(),
            description=f"```{f.text}```",
        )

        category = None
        if data.get("category"):
            category = f' | {data.get("category")}'

        embed.set_author(
            name=f'Anime News Network News | {data.get("date").replace("-0500", "EST")}'
            f'{category if data.get("category") else ""}'
        )

        embed.set_footer(
            text=f"Provided by https://www.animenewsnetwork.com/ • Page {page}/{pages}"
        )

        return embed

    @staticmethod
    async def get_crunchynews_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `crunchynews` embed.
        Args:
            data (dict): The data about the anime news.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        # thanks stackoverflow
        f = HTMLFilter()
        f.feed(data.get("description"))
        embed = discord.Embed(
            title=data.get("title"),
            url=data.get("link"),
            color=discord.Color.random(),
            description=f"```{f.text}```",
        )

        embed.set_author(name=f'Crunchyroll News | {data.get("date")}')

        embed.set_footer(text=f"Provided by https://www.crunchyroll.com/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_next_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `next` embed.
        Args:
            data (dict): The data about the next airing anime episode.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        sites = []
        if data.get("media").get("siteUrl"):
            sites.append(f'[Anilist]({data.get("media").get("siteUrl")})')
        if data.get("media").get("idMal"):
            sites.append(
                f'[MyAnimeList](https://myanimelist.net/anime/{str(data.get("media").get("idMal"))})'
            )
        if data.get("media").get("trailer"):
            if data.get("media").get("trailer")["site"] == "youtube":
                sites.append(
                    f'[Trailer](https://www.youtube.com/watch?v={data.get("media").get("trailer")["id"]})'
                )
        if data.get("media").get("externalLinks"):
            for i in data.get("media").get("externalLinks"):
                sites.append(f'[{i["site"]}]({i["url"]})')

        embed = discord.Embed(
            title=get_media_title(data.get("media")["title"]),
            colour=discord.Color.random(),
            description=f'Episode **{data.get("episode")}** airing in '
            f'**{str(datetime.timedelta(seconds=data.get("timeUntilAiring")))}**.\n\n**Type:** '
            f'{format_media_type(data.get("media")["format"]) if data.get("media")["format"] else "N/A"}'
            f"\n**Duration:** "
            f'{str(data.get("media")["duration"]) + " min" if data.get("media")["duration"] else "N/A"}\n'
            f'\n{" | ".join(sites) if len(sites) > 0 else ""}',
        )

        embed.set_author(name="Next Airing Episode")

        if data.get("media").get("coverImage").get("large"):
            embed.set_thumbnail(url=data.get("media")["coverImage"]["large"])

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_last_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """
        Returns the `last` embed.
        Args:
            data (dict): The data about the recently aired anime episode.
            page (int): The current page.
            pages (page): The number of all pages.
        Returns:
            Embed: A discord embed.
        """
        sites = []
        if data.get("media").get("siteUrl"):
            sites.append(f'[Anilist]({data.get("media").get("siteUrl")})')
        if data.get("media").get("idMal"):
            sites.append(
                f'[MyAnimeList](https://myanimelist.net/anime/{str(data.get("media").get("idMal"))})'
            )
        if data.get("media").get("trailer"):
            if data.get("media").get("trailer")["site"] == "youtube":
                sites.append(
                    f'[Trailer](https://www.youtube.com/watch?v={data.get("media").get("trailer")["id"]})'
                )
        if data.get("media").get("externalLinks"):
            for i in data.get("media").get("externalLinks"):
                sites.append(f'[{i["site"]}]({i["url"]})')

        date = datetime.datetime.utcfromtimestamp(data.get("airingAt")).strftime(
            "%B %d, %Y - %H:%M"
        )

        embed = discord.Embed(
            title=get_media_title(data.get("media")["title"]),
            colour=discord.Color.random(),
            description=f'Episode **{data.get("episode")}** aired at **{str(date)}** UTC.\n\n**Type:** '
            f'{format_media_type(data.get("media")["format"]) if data.get("media")["format"] else "N/A"}'
            f"\n**Duration:** "
            f'{str(data.get("media")["duration"]) + " min" if data.get("media")["duration"] else "N/A"}\n'
            f'\n{" | ".join(sites) if len(sites) > 0 else ""}',
        )

        embed.set_author(name="Recently Aired Episode")

        if data.get("media").get("coverImage").get("large"):
            embed.set_thumbnail(url=data.get("media")["coverImage"]["large"])

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    @commands.command(name="anime", aliases=["ani"], ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def anime(self, ctx: Context, *, title: str):
        """
        Searches for an anime with the given title and displays information about the search results such as type,
        status, episodes, description, and more!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, title, AniListSearchType.ANIME)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The anime `{title}` could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="manga", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def manga(self, ctx: Context, *, title: str):
        """
        Searches for a manga with the given title and displays information about the search results such as type,
        status, chapters, description, and more!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, title, AniListSearchType.MANGA)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The manga `{title}` could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="character", aliases=["char"], ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def character(self, ctx: Context, *, name: str):
        """
        Searches for a character with the given name and displays information about the search results such as
        description, synonyms, and appearances!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, name, AniListSearchType.CHARACTER)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The character `{name}` could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="anistaff", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def anstaff(self, ctx: Context, *, name: str):
        """
        Searches for a staff with the given name and displays information about the search results such as description,
        staff roles, and character roles!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, name, AniListSearchType.STAFF)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The staff `{name}` could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="studio", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def studio_(self, ctx: Context, *, name: str):
        """
        Searches for a studio with the given name and displays information about the search results such as the studio
        productions!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, name, AniListSearchType.STUDIO)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The studio `{name}` could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="random", ignore_extra=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def rnd(self, ctx: Context, media: str, *, genre: str):
        """
        Displays a random anime or manga of the specified genre.
        """
        async with ctx.channel.typing():
            if media.lower() == AniListMediaType.ANIME.value.lower():
                embed = await self.anilist_random(
                    ctx,
                    genre,
                    AniListMediaType.ANIME,
                    ["TV", "MOVIE", "OVA", "ONA", "TV_SHORT", "MUSIC", "SPECIAL"],
                )
                if not embed:
                    embed = discord.Embed(
                        title=f"An anime with the genre `{genre}` could not be found.",
                        color=discord.Color.random(),
                    )
                await ctx.channel.send(embed=embed)
            elif media.lower() == AniListMediaType.MANGA.value.lower():
                embed = await self.anilist_random(
                    ctx, genre, AniListMediaType.MANGA, ["MANGA", "ONE_SHOT", "NOVEL"]
                )
                if not embed:
                    embed = discord.Embed(
                        title=f"A manga with the genre `{genre}` could not be found.",
                        color=discord.Color.random(),
                    )
                await ctx.channel.send(embed=embed)
            else:
                ctx.command.reset_cooldown(ctx)
                raise discord.ext.commands.BadArgument

    #    @commands.command(name='themes', ignore_extra=False)
    #    @commands.cooldown(1, 5, commands.BucketType.user)
    #    async def themes(self, ctx: Context, *, anime: str):
    #        """
    #        Searches for the openings and endings of the given anime and displays them.
    #        """
    #        async with ctx.channel.typing():
    #            data = await self.animethemes.search(anime, 5, ['anime'])
    #              embeds = []
    #              for page, entry in enumerate(data.get('search').get('anime')):
    #                 try:
    #                    embed = await self.get_themes_embed(entry, page + 1, len(data.get('search').get('anime')))
    #               except Exception as e:
    #                  log.exception(e)
    #                 embed = discord.Embed(
    #                    title='Error', color=discord.Color.random(),
    #                   description=f'An error occurred while loading the embed for the anime.')
    #              embed.set_footer(
    #                 text=f'Provided by https://animethemes.moe/ • Page '
    #                     f'{page + 1}/{len(data.get("search").get("anime"))}')
    #       embeds.append(embed)
    #  menu = menus.MenuPages(source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30)
    # await menu.start(ctx)
    # else:
    #    embed = discord.Embed(title=f'No themes for the anime `{anime}` found.', color=discord.Color.random())
    #   await ctx.channel.send(embed=embed)

    #   @commands.command(name='theme', ignore_extra=False)
    #  @commands.cooldown(1, 5, commands.BucketType.user)
    # async def theme(self, ctx: Context, theme: str, *, anime: str):
    #    """
    #   Displays a specific opening or ending of the given anime.
    #  """
    # async with ctx.channel.typing():
    #    data = await self.animethemes.search(anime, 1, ['anime'])
    #   if data.get('search').get('anime'):
    #      anime_ = data.get('search').get('anime')[0]
    #     for entry in anime_.get('themes'):
    #        if theme.upper() == entry.get('slug') or \
    #               (theme.upper() == 'OP' and entry.get('slug') == 'OP1') or \
    #              (theme.upper() == 'ED' and entry.get('slug') == 'ED1') or \
    #             (theme.upper() == 'OP1' and entry.get('slug') == 'OP') or \
    #            (theme.upper() == 'ED1' and entry.get('slug') == 'ED'):
    #       try:
    #          embed = await self.get_theme_embed(anime_, entry)
    #     except Exception as e:
    #        log.exception(e)
    #       embed = discord.Embed(
    #          title='Error', color=discord.Color.random(),
    #         description=f'An error occurred while loading the embed for the theme.')
    #    embed.set_footer(
    #       text=f'Provided by https://animethemes.moe/')
    # await ctx.channel.send(embed=embed)
    # return await ctx.channel.send(
    #   f'http://animethemes.moe/video/{entry.get("entries")[0]["videos"][0]["basename"]}')
    #            embed = discord.Embed(
    #               title=f'Cannot find `{theme.upper()}` for the anime `{anime}`.', color=discord.Color.random())
    #          await ctx.channel.send(embed=embed)
    #     else:
    #        embed = discord.Embed(title=f'No theme for the anime `{anime}` found.', color=discord.Color.random())
    #       await ctx.channel.send(embed=embed)

    @commands.command(name="next", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def next(self, ctx: Context):
        """
        Displays the next airing anime episodes.
        """
        async with ctx.channel.typing():
            try:
                data = await self.anilist.schedule(
                    page=1, perPage=15, notYetAired=True, sort="TIME"
                )
            except Exception as e:
                log.exception(e)
                embed = discord.Embed(
                    title=f"An error occurred while searching for the next airing episodes. Try again.",
                    color=discord.Color.random(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, anime in enumerate(data):
                    try:
                        embed = await self.get_next_embed(anime, page + 1, len(data))
                    except Exception as e:
                        log.exception(e)
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.random(),
                            description=f"An error occurred while loading the embed for the next airing episode.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The next airing episodes could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="last", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def last(self, ctx: Context):
        """
        Displays the most recently aired anime episodes.
        """
        async with ctx.channel.typing():
            try:
                data = await self.anilist.schedule(
                    page=1, perPage=15, notYetAired=False, sort="TIME_DESC"
                )
            except Exception as e:
                log.exception(e)
                embed = discord.Embed(
                    title=f"An error occurred while searching for the most recently aired episodes. Try again.",
                    color=discord.Color.random(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, anime in enumerate(data):
                    try:
                        embed = await self.get_last_embed(anime, page + 1, len(data))
                    except Exception as e:
                        log.exception(e)
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.random(),
                            description=f"An error occurred while loading the embed for the recently aired episode.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds),
                    clear_reactions_after=True,
                    timeout=30,
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The most recently aired episodes could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="aninews", ignore_extra=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def aninews(self, ctx: Context):
        """
        Displays the latest anime news from Anime News Network.
        """
        async with ctx.channel.typing():
            try:
                data = await self.animenewsnetwork.news(count=15)
            except Exception as e:
                log.exception(e)
                embed = discord.Embed(
                    title=f"An error occurred while searching for the Anime News Network news. Try again.",
                    color=discord.Color.random(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, news in enumerate(data):
                    try:
                        embed = await self.get_aninews_embed(news, page + 1, len(data))
                    except Exception as e:
                        log.exception(e)
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.random(),
                            description=f"An error occurred while loading the embed for the Anime News Network news.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://www.animenewsnetwork.com/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The Anime News Network news could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="crunchynews", aliases=["crnews"], ignore_extra=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def crunchynews(self, ctx: Context):
        """
        Displays the latest anime news from Crunchyroll.
        """
        async with ctx.channel.typing():
            try:
                data = await self.crunchyroll.news(count=15)
            except Exception as e:
                log.exception(e)
                embed = discord.Embed(
                    title=f"An error occurred while searching for the Crunchyroll news. Try again.",
                    color=discord.Color.random(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, news in enumerate(data):
                    try:
                        embed = await self.get_crunchynews_embed(news, page + 1, len(data))
                    except Exception as e:
                        log.exception(e)
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.random(),
                            description=f"An error occurred while loading the embed for the Crunchyroll news.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://www.crunchyroll.com/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The Crunchyroll news could not be found.",
                    color=discord.Color.random(),
                )
                await ctx.channel.send(embed=embed)
