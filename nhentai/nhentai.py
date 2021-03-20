import datetime
from typing import Optional

import discord
import nhentaio
from redbot.core import commands
from redbot.core.utils._dpy_menus_utils import SimpleHybridMenu, SimpleSource

client = nhentaio.Client()


def nsfwcheck():
    """
    Custom check that hide all commands used with it in the help formatter
    and block usage of them if used in a non-nsfw channel.
    taken from https://github.com/PredaaA/predacogs/blob/2a27589abeb94666a74d5f1bed84b303d95a0e47/nsfw/core.py#L206
    """

    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return True
        if ctx.channel.is_nsfw():
            return True
        if ctx.invoked_with == "help" and not ctx.channel.is_nsfw():
            return False
        if ctx.invoked_with not in [k for k in ctx.bot.all_commands]:
            # From https://github.com/PredaaA/predacogs/blob/2a27589abeb94666a74d5f1bed84b303d95a0e47/nsfw/core.py#L206
            # thanks preda
            return False
        msg = "You can't use this command in a non-NSFW channel !"
        try:
            embed = discord.Embed(title="\N{LOCK} " + msg, color=0xAA0000)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(msg)
        finally:
            return False

    return commands.check(predicate)


class Embed(discord.Embed):
    def __init__(self, colour=discord.Color.random(), timestamp=None, **kwargs):
        super(Embed, self).__init__(
            colour=colour, timestamp=timestamp or datetime.datetime.utcnow(), **kwargs
        )

    @classmethod
    def default(cls, ctx, **kwargs):
        instance = cls(**kwargs)
        instance.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        return instance


class Nhentai(commands.Cog):
    """
    Nhentai.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @nsfwcheck()
    async def nhentai(self, ctx: commands.Context):
        """Some nhentai related commands."""

    @commands.cooldown(rate=1, per=5)
    @nhentai.command()
    async def info(self, ctx: commands.Context, doujin):
        """Info on a doujin on nhentai."""
        if not doujin.isdigit():
            return await ctx.reply("Use some digits stupid.")
        gallery = await client.fetch_gallery(doujin)
        emb = Embed.default(ctx)
        emb.title = gallery.title
        emb.set_image(url=gallery.cover.url)
        msg = ""
        for tag in gallery.tags:
            msg += f"`{tag.name}` | `{tag.name}` | `{tag.name}`\n"
        emb.add_field(name="Tags", value=msg)
        await ctx.reply(embed=emb)

    @nhentai.group()
    async def search(self, ctx: commands.Context):
        """Search something on nhentai based on tags or just the name."""

    @commands.cooldown(rate=1, per=5)
    @search.command()
    async def tag(self, ctx: commands.Context, tag, sort_by: Optional[str]):
        """
        Search for doujins with the specified tag
        Options for sorting are: recent, popular_today, popular_this_week, popular_this_month
        """
        embed_list = []
        if not sort_by:
            async for result in client.search(tag):
                embed = Embed.default(ctx)
                embed.set_image(url=result.thumbnail.url)
                embed.title = result.title
                embed.set_author(name=result.id)
                embed_list.append(embed)
        else:
            horny = f"SortType.{sort_by}"
            async for result in client.search(tag, sort_by=horny):
                embed = Embed.default(ctx)
                embed.set_image(url=result.thumbnail.url)
                embed.title = result.title
                embed.set_author(name=result.id)
                embed_list.append(embed)
        await SimpleHybridMenu(
            source=SimpleSource(pages=embed_list),
            cog=self,
            delete_message_after=True,
        ).start(ctx=ctx, wait=False)

    @commands.cooldown(rate=1, per=5)
    @search.command()
    async def name(self, ctx: commands.Context, *, name):
        """Look for doujins using names on nhentai."""
        try:
            embed_list = []
            async for result in client.search(name):
                embed = Embed.default(ctx)
                embed.set_image(url=result.thumbnail.url)
                embed.title = result.title
                embed.set_author(name=result.id)
                embed_list.append(embed)

            await SimpleHybridMenu(
                source=SimpleSource(pages=embed_list),
                cog=self,
                delete_message_after=True,
            ).start(ctx=ctx, wait=False)

        except nhentaio.NotFound:
            await ctx.reply("Too bad your delusional taste doesn't exist here.")

    @commands.cooldown(rate=1, per=5)
    @nhentai.command()
    async def read(self, ctx: commands.Context, doujin):
        """Read some cultured doujins"""
        if not doujin.isdigit():
            return await ctx.reply("Use some digits you pervert.")
        gallery = await client.fetch_gallery(doujin)
        embed_list = []
        for page in gallery.pages:
            embed = Embed.default(ctx)
            embed.title = gallery.title
            embed.set_image(url=page.content.url)
            embed_list.append(embed)
        await SimpleHybridMenu(
            source=SimpleSource(pages=embed_list),
            cog=self,
            delete_message_after=True,
        ).start(ctx=ctx, wait=False)
