import discord
from discord.ext import commands

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(error)
        if isinstance(error, commands.CommandNotFound):
            embed=discord.Embed(title="**Command Not Found**", description="The command you typed was not found. See `help` for a list of all the commands available.", color=0xe01b24)
            await ctx.send(embed=embed)
