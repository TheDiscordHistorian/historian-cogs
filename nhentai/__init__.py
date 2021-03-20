from .nhentai import Nhentai


async def setup(bot):
    bot.add_cog(Nhentai(bot))
