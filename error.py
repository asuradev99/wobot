import discord
from discord.ext import commands

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(str(type(error)) + str(error))
        if isinstance(error, commands.CommandNotFound):
            embed=discord.Embed(title="**Command Not Found**", description="The command you typed was not found. See `help` for a list of all the commands available.", color=0xe01b24)
            
        if isinstance(error, (commands.errors.CommandInvokeError)):
            embed=discord.Embed(title="**Command Error**", description=f"{str(error.original)}", color=0xe01b24)
            
            print(error.original)
        if isinstance(error, (commands.errors.MissingPermissions) ):
            embed=discord.Embed(title="**Permission Error**", description=f"You don't have permission to use that command!", color=0xe01b24)
        await ctx.send(embed=embed)
        
