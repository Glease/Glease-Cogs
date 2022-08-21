from .scrape import MyCog


def setup(bot):
    bot.add_cog(MyCog(bot))
