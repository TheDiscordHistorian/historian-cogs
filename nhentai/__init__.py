from .nhentai import NhentaiCog


async def setup(bot):
    bot.add_cog(NhentaiCog(bot))
