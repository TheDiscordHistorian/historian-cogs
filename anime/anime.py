import logging

import aiohttp
import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.vendored.discord.ext import menus

from .utility import (AniListMediaType, AniListSearchType, AnimeThemesClient,
                      EmbedListMenu, is_adult)
from .utils.anilist import AniListClient
from .utils.animenewsnetwork import AnimeNewsNetworkClient
from .utils.crunchyroll import CrunchyrollClient
from .utils.finder import Finder

log = logging.getLogger("red.historian.anime")


class Anime(Finder, commands.Cog):
    """Search for anime, manga, characters and users using Anilist"""

    __version__ = "1.5.0"
    __author__ = "`kato#0666` and `❥²#0666`"
    # from https://github.com/flaree/Flare-Cogs/blob/9ba8c884b0f78f5f2fffce9efec1ca6c8ac600ea/joinmessage/joinmessage.py#L49
    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.anilist = AniListClient(session=self.session)
        self.animethemes = AnimeThemesClient(
            session=self.session, headers={"User-Agent": "Some Discord Bot"}
        )
        self.animenewsnetwork = AnimeNewsNetworkClient(session=self.session)
        self.crunchyroll = CrunchyrollClient(session=self.session)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command(name="anime", aliases=["ani"], usage="anime <title>", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def anime(self, ctx: Context, *, title: str):
        """
        Searches for an anime with the given title and displays information about the search results such as type,
        status, episodes, description, and more!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, title, AniListSearchType.Anime)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The anime `{title}` could not be found.", color=discord.Color.random()
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="manga", usage="manga <title>", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def manga(self, ctx: Context, *, title: str):
        """
        Searches for a manga with the given title and displays information about the search results such as type,
        status, chapters, description, and more!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, title, AniListSearchType.Manga)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                  title=f"The manga `{title}` could not be found.", color=discord.Color.red()
                )
                await ctx.channel.send(embed=embed)

    @commands.command(
        name="character", aliases=["char"], usage="character <name>", ignore_extra=False
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def character(self, ctx: Context, *, name: str):
        """
        Searches for a character with the given name and displays information about the search results such as
        description, synonyms, and appearances!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, name, AniListSearchType.Character)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                  title=f"The character `{name}` could not be found.",
                  color=discord.Color.red(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="anistaff", usage="anistaff <name>", ignore_extra=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def anistaff(self, ctx: Context, *, name: str):
        """
        Searches for a staff with the given name and displays information about the search results such as description,
        staff roles, and character roles!
        """
        async with ctx.channel.typing():
            embeds = await self.anilist_search(ctx, name, AniListSearchType.Staff)
            if embeds:
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                  title=f"The staff `{name}` could not be found.", color=discord.Color.red()
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
            embeds = await self.anilist_search(ctx, name, AniListSearchType.Studio)
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
            if media.lower() == AniListMediaType.Anime.lower():
                embed = await self.anilist_random(
                    ctx,
                    genre,
                    AniListMediaType.Anime.upper(),
                    ["TV", "MOVIE", "OVA", "ONA", "TV_SHORT", "MUSIC", "SPECIAL"],
                )
                if not embed:
                    embed = discord.Embed(
                        title=f"An anime with the genre `{genre}` could not be found.",
                        color=discord.Color.random(),
                    )
                await ctx.channel.send(embed=embed)
            elif media.lower() == AniListMediaType.Manga.lower():
                embed = await self.anilist_random(
                    ctx, genre, AniListMediaType.Manga.upper(), ["MANGA", "ONE_SHOT", "NOVEL"]
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

    @commands.command(name="themes", usage="themes <anime>", ignore_extra=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def themes(self, ctx: Context, *, anime: str):
        """
        Searches for the openings and endings of the given anime and displays them.
        """
        async with ctx.channel.typing():
            data = await self.animethemes.search(anime, 15)
            if data.get("search").get("anime"):
                embeds = []
                for page, entry in enumerate(data.get("search").get("anime")):
                    try:
                        embed = await self.get_themes_embed(
                            entry, page + 1, len(data.get("search").get("anime"))
                        )
                        if not isinstance(ctx.channel, discord.channel.DMChannel):
                            if (
                                is_adult(entry.get("themes")[0]["entries"][0])
                                and not ctx.channel.is_nsfw()
                            ):
                                embed = discord.Embed(
                                    title="Error",
                                    color=discord.Color.red(),
                                    description=f"Adult content. No NSFW channel.",
                                )
                                embed.set_footer(
                                    text=f"Provided by https://animethemes.moe/ • Page {page + 1}/"
                                    f'{len(data.get("search").get("anime"))}'
                                )
                    except Exception as e:
                        log.exception(e)
                        embed = discord.Embed(
                            title="Error",
                            color=discord.Color.red(),
                            description=f"An error occurred while loading the embed for the anime.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://animethemes.moe/ • Page "
                            f'{page + 1}/{len(data.get("search").get("anime"))}'
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"No themes for the anime `{anime}` found.", color=discord.Color.red()
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="theme", usage="theme <OP|ED> <anime>", ignore_extra=False)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def theme(self, ctx: Context, theme: str, *, anime: str):
        """
        Displays a specific opening or ending of the given anime.
        """
        async with ctx.channel.typing():
            data = await self.animethemes.search(anime, 1)
            if data.get("search").get("anime"):
                anime_ = data.get("search").get("anime")[0]
                if anime_.get("themes"):
                    for entry in anime_.get("themes"):
                        if (
                            theme.upper() == entry.get("slug")
                            or (theme.upper() == "OP" and entry.get("slug") == "OP1")
                            or (theme.upper() == "ED" and entry.get("slug") == "ED1")
                            or (theme.upper() == "OP1" and entry.get("slug") == "OP")
                            or (theme.upper() == "ED1" and entry.get("slug") == "ED")
                        ):
                            try:
                                embed = await self.get_theme_embed(anime_, entry)
                                if not isinstance(ctx.channel, discord.channel.DMChannel):
                                    if (
                                        is_adult(entry.get("entries")[0])
                                        and not ctx.channel.is_nsfw()
                                    ):
                                        embed = discord.Embed(
                                            title="Error",
                                            color=discord.Color.red(),
                                            description=f"Adult content. No NSFW channel.",
                                        )
                                        embed.set_footer(
                                            text=f"Provided by https://animethemes.moe/"
                                        )
                                        return await ctx.channel.send(embed=embed)
                            except Exception as e:
                                log.exception(e)
                                embed = discord.Embed(
                                    title="Error",
                                    color=discord.Color.red(),
                                    description=f"An error occurred while loading the embed for the theme.",
                                )
                                embed.set_footer(text=f"Provided by https://animethemes.moe/")
                            await ctx.channel.send(embed=embed)
                            return await ctx.channel.send(
                                f'https://animethemes.moe/video/{entry.get("entries")[0]["videos"][0]["basename"]}'
                            )
                    embed = discord.Embed(
                        title=f"Cannot find `{theme.upper()}` for the anime `{anime}`.",
                        color=discord.Color.red(),
                    )
                    await ctx.channel.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title=f"Cannot find `{theme.upper()}` for the anime `{anime}`.",
                        color=discord.Color.red(),
                    )
                    await ctx.channel.send(embed=embed)
            else:
                embed = discord.Embed(
                    title=f"No theme for the anime `{anime}` found.", color=discord.Color.red()
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="next", usage="next", ignore_extra=False)
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
                    color=discord.Color.red(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, anime in enumerate(data):
                    try:
                        embed = await self.get_next_embed(anime, page + 1, len(data))
                        if not isinstance(ctx.channel, discord.channel.DMChannel):
                            if is_adult(anime.get("media")) and not ctx.channel.is_nsfw():
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
                            description=f"An error occurred while loading the embed for the next airing episode.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The next airing episodes could not be found.",
                    color=discord.Color.red(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="last", usage="last", ignore_extra=False)
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
                    color=discord.Color.red(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, anime in enumerate(data):
                    try:
                        embed = await self.get_last_embed(anime, page + 1, len(data))
                        if not isinstance(ctx.channel, discord.channel.DMChannel):
                            if is_adult(anime.get("media")) and not ctx.channel.is_nsfw():
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
                            description=f"An error occurred while loading the embed for the recently aired episode.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"The most recently aired episodes could not be found.",
                    color=discord.Color.red(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(name="aninews", usage="aninews", ignore_extra=False)
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
                    color=discord.Color.red(),
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
                            color=discord.Color.red(),
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
                    color=discord.Color.red(),
                )
                await ctx.channel.send(embed=embed)

    @commands.command(
        name="crunchynews", aliases=["crnews"], usage="crunchynews", ignore_extra=False
    )
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
                    color=discord.Color.red(),
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
                            color=discord.Color.red(),
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
                    title=f"The Crunchyroll news could not be found.", color=discord.Color.red()
                )
                await ctx.channel.send(embed=embed)

    @commands.command(
        name="trending", aliases=["trend"], usage="trending <anime|manga>", ignore_extra=False
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def trending(self, ctx: Context, media: str):
        """
        Displays the current trending anime or manga on AniList.
        """
        async with ctx.channel.typing():
            if media.lower() == AniListMediaType.Anime.lower():
                type_ = AniListMediaType.Anime.upper()
            elif media.lower() == AniListMediaType.Manga.lower():
                type_ = AniListMediaType.Manga.upper()
            else:
                ctx.command.reset_cooldown(ctx)
                raise discord.ext.commands.BadArgument
            try:
                data = await self.anilist.trending(
                    page=1, perPage=10, type=type_, sort="TRENDING_DESC"
                )
            except Exception as e:
                log.exception(e)
                embed = discord.Embed(
                    title=f"An error occurred while searching for the trending {type_.lower()}. "
                    f"Try again.",
                    color=discord.Color.red(),
                )
                return await ctx.channel.send(embed=embed)
            if data is not None and len(data) > 0:
                embeds = []
                for page, entry in enumerate(data):
                    try:
                        embed = await self.get_media_embed(entry, page + 1, len(data))
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
                            description=f"An error occurred while loading the embed for the "
                            f"{type_.lower()}.",
                        )
                        embed.set_footer(
                            text=f"Provided by https://anilist.co/ • Page {page + 1}/{len(data)}"
                        )
                    embeds.append(embed)
                menu = menus.MenuPages(
                    source=EmbedListMenu(embeds), clear_reactions_after=True, timeout=30
                )
                await menu.start(ctx)
            else:
                embed = discord.Embed(
                    title=f"No trending {type_.lower()} found.", color=discord.Color.red()
                )
                await ctx.channel.send(embed=embed)
