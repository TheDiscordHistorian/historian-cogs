from .anime import Anime


async def setup(bot):
    n = Anime(bot)
    bot.add_cog(n)
