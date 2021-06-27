import datetime
import html
import logging
import random
from typing import Any, Dict, List, Optional, Union

import discord
from discord import Embed
from discord.ext.commands import Context

from ..utility import (AniListSearchType, clean_html, format_anime_status,
                       format_date, format_description, format_manga_status,
                       format_media_type, is_adult)

log = logging.getLogger("red.historian.anime")


class Finder:
    """Finder Module"""

    @staticmethod
    async def get_next_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """Returns the next embed."""
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
            colour=discord.Color.random(),
            description=f'Episode **{data.get("episode")}** airing in '
            f'**{str(datetime.timedelta(seconds=data.get("timeUntilAiring")))}**.\n\n**Type:** '
            f'{format_media_type(data.get("media")["format"]) if data.get("media")["format"] else "N/A"}'
            f"\n**Duration:** "
            f'{str(data.get("media")["duration"]) + " min" if data.get("media")["duration"] else "N/A"}\n'
            f'\n{" | ".join(sites) if len(sites) > 0 else ""}',
        )

        if (
            data.get("media")["title"]["english"] is None
            or data.get("media")["title"]["english"] == data.get("media")["title"]["romaji"]
        ):
            embed.title = data.get("media")["title"]["romaji"]
        else:
            embed.title = (
                f'{data.get("media")["title"]["romaji"]} ({data.get("media")["title"]["english"]})'
            )

        embed.set_author(name="Next Airing Episode")

        if data.get("media").get("coverImage").get("large"):
            embed.set_thumbnail(url=data.get("media")["coverImage"]["large"])

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_last_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """Returns the `last` embed."""
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
            colour=discord.Color.random(),
            description=f'Episode **{data.get("episode")}** aired at **{str(date)}** UTC.\n\n**Type:** '
            f'{format_media_type(data.get("media")["format"]) if data.get("media")["format"] else "N/A"}'
            f"\n**Duration:** "
            f'{str(data.get("media")["duration"]) + " min" if data.get("media")["duration"] else "N/A"}\n'
            f'\n{" | ".join(sites) if len(sites) > 0 else ""}',
        )

        if (
            data.get("media")["title"]["english"] is None
            or data.get("media")["title"]["english"] == data.get("media")["title"]["romaji"]
        ):
            embed.title = data.get("media")["title"]["romaji"]
        else:
            embed.title = (
                f'{data.get("media")["title"]["romaji"]} ({data.get("media")["title"]["english"]})'
            )

        embed.set_author(name="Recently Aired Episode")

        if data.get("media").get("coverImage").get("large"):
            embed.set_thumbnail(url=data.get("media")["coverImage"]["large"])

        embed.set_footer(text=f"Provided by https://anilist.co/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_themes_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """Returns the themes embed."""
        embed = discord.Embed(color=discord.Color.random(), title=data.get("name"))

        embed.set_author(name="Themes")

        if data.get("images"):
            embed.set_thumbnail(url=data.get("images")[0]["link"])

        if data.get("resources"):
            embed.description = " | ".join(
                [f'[{site.get("site")}]({site.get("link")})' for site in data.get("resources")]
            )

        count = 1
        for theme in data.get("themes"):
            if count >= 15:
                embed.add_field(name=theme.get("slug"), value="...", inline=False)
                break
            count += 1

            list_ = ["**Title:** " + theme.get("song")["title"]]

            if theme.get("song")["artists"]:
                list_.append("**Artist:** " + theme.get("song")["artists"][0]["name"])

            link = f'[Link](https://animethemes.moe/video/{theme.get("entries")[0]["videos"][0]["basename"]})'
            list_.append(link)

            embed.add_field(name=theme.get("slug"), value="\n".join(list_), inline=False)

        embed.set_footer(text=f"Provided by https://animethemes.moe/ • Page {page}/{pages}")

        return embed

    @staticmethod
    async def get_theme_embed(anime: Dict[str, Any], data: Dict[str, Any]) -> Embed:
        """Returns the theme embed."""
        embed = discord.Embed(color=discord.Color.random(), title=anime.get("name"))

        embed.set_author(name=data.get("slug").replace("OP", "Opening ").replace("ED", "Ending "))

        if anime.get("images"):
            embed.set_thumbnail(url=anime.get("images")[0]["link"])

        list_ = []

        if anime.get("resources"):
            list_.append(
                " | ".join(
                    [
                        f'[{site.get("site")}]({site.get("link")})'
                        for site in anime.get("resources")
                    ]
                )
                + "\n"
            )

        list_.append("**Title:** " + data.get("song")["title"])

        if data.get("song")["artists"]:
            list_.append(
                "**Artist:** " + data.get("song")["artists"][0]["name"]
                if len(data.get("song")["artists"]) == 1
                else "**Artists:** "
                + ", ".join([a.get("name") for a in data.get("song")["artists"]])
            )

        embed.description = "\n".join(list_) if len(list_) > 0 else "N/A"

        embed.set_footer(text=f"Provided by https://animethemes.moe/")

        return embed

    @staticmethod
    async def get_aninews_embed(data: Dict[str, Any], page: int, pages: int) -> Embed:
        """Returns the aninews embed."""
        embed = discord.Embed(
            title=data.get("title"),
            url=data.get("link"),
            color=discord.Color.random(),
            description=f'```{html.unescape(clean_html(data.get("description"))).rstrip()}```',
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
        """Returns the crunchynews embed."""
        embed = discord.Embed(
            title=data.get("title"),
            url=data.get("link"),
            color=discord.Color.random(),
            description=f'```{html.unescape(clean_html(data.get("description"))).rstrip()}```',
        )

        embed.set_author(name=f'Crunchyroll News | {data.get("date")}')

        embed.set_footer(text=f"Provided by https://www.crunchyroll.com/ • Page {page}/{pages}")

        return embed

    async def anilist_search(
        self, ctx: Context, search: str, type_: str
    ) -> Union[List[Embed], None]:
        """Returns a list of Discord embeds with the retrieved anilist data about the searched entry."""
        embeds = []
        data = None

        try:
            if type_ == AniListSearchType.Anime:
                data = await self.anilist.media(
                    search=search, page=1, perPage=15, type=type_.upper()
                )
            elif type_ == AniListSearchType.Manga:
                data = await self.anilist.media(
                    search=search, page=1, perPage=15, type=type_.upper()
                )
            elif type_ == AniListSearchType.Character:
                data = await self.anilist.character(search=search, page=1, perPage=15)
            elif type_ == AniListSearchType.Staff:
                data = await self.anilist.staff(search=search, page=1, perPage=15)
            elif type_ == AniListSearchType.Studio:
                data = await self.anilist.studio(search=search, page=1, perPage=15)

        except Exception as e:
            log.exception(e)

            embed = discord.Embed(
                title=f"An error occurred while searching for the {type_.lower()} `{search}`. Try again.",
                color=discord.Color.red(),
            )
            embeds.append(embed)

            return embeds

        if data is not None:
            for page, entry in enumerate(data):

                embed = None

                try:
                    if type_ == AniListSearchType.Anime:
                        embed = await self.get_media_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.Manga:
                        embed = await self.get_media_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.Character:
                        embed = await self.get_character_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.Staff:
                        embed = await self.get_staff_embed(entry, page + 1, len(data))
                    elif type_ == AniListSearchType.Studio:
                        embed = await self.get_studio_embed(entry, page + 1, len(data))

                    if not isinstance(ctx.channel, discord.channel.DMChannel):
                        if is_adult(entry) and not ctx.channel.is_nsfw():
                            embed = discord.Embed(
                                title="Error",
                                color=discord.Color.red(),
                                description=f"Adult content. No NSFW channel.",
                            )
                            embed.set_footer(
                                text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                            )

                except Exception as e:
                    log.exception(e)

                    embed = discord.Embed(
                        title="Error",
                        color=discord.Color.red(),
                        description=f"An error occurred while loading the embed for the {type_.lower()}.",
                    )
                    embed.set_footer(
                        text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                    )

                embeds.append(embed)

            return embeds
        return None

    async def anilist_random(
        self, ctx: Context, search: str, type_: str, format_in: List[str]
    ) -> Union[Embed, None]:
        """Returns a Discord embed with the retrieved anilist data about a random media of a specified genre."""
        try:

            data = await self.anilist.genre(
                genre=search, page=1, perPage=1, type=type_, format_in=format_in
            )

            if (
                data.get("data")["Page"]["media"] is not None
                and len(data.get("data")["Page"]["media"]) > 0
            ):
                page = random.randrange(1, data.get("data")["Page"]["pageInfo"]["lastPage"])
                data = await self.anilist.genre(
                    genre=search, page=page, perPage=1, type=type_, format_in=format_in
                )

            else:

                data = await self.anilist.tag(
                    tag=search, page=1, perPage=1, type=type_, format_in=format_in
                )

                if (
                    data.get("data")["Page"]["media"] is not None
                    and len(data.get("data")["Page"]["media"]) > 0
                ):
                    page = random.randrange(1, data.get("data")["Page"]["pageInfo"]["lastPage"])
                    data = await self.anilist.tag(
                        tag=search, page=page, perPage=1, type=type_, format_in=format_in
                    )
                else:
                    return None

        except Exception as e:
            log.exception(e)

            embed = discord.Embed(
                title=f"An error occurred while searching for a {type_.lower()} with the genre `{search}`.",
                color=discord.Color.red(),
            )

            return embed

        if (
            data.get("data")["Page"]["media"] is not None
            and len(data.get("data")["Page"]["media"]) > 0
        ):

            try:
                embed = await self.get_media_embed(data.get("data")["Page"]["media"][0])

                if not isinstance(ctx.channel, discord.channel.DMChannel):
                    if (
                        is_adult(data.get("data")["Page"]["media"][0])
                        and not ctx.channel.is_nsfw()
                    ):
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.red(),
                            description=f"Adult content. No NSFW channel.",
                        )

            except Exception as e:
                log.exception(e)

                embed = discord.Embed(
                    title=f"An error occurred while searching for a {type_.lower()} with the genre `{search}`.",
                    color=discord.Color.red(),
                )

            return embed

        return None

    @staticmethod
    async def get_media_embed(
        data: Dict[str, Any], page: Optional[int] = None, pages: Optional[int] = None
    ) -> Embed:
        """Returns the media embed."""
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
        """Returns the character embed."""
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
        """Returns the staff embed."""
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
        """Returns the studio embed."""
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
