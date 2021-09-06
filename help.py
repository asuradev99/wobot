import discord

from discord import Embed
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help', aliases=['h'], brief=f'Lists and displays information about the available commands.')
    async def help(self, ctx, help_command=None):
        emb = Embed(
            title="Commands",
            description=""
        )
        if not help_command: 
            for command in self.bot.commands:
                emb.description += '`' + command.name + '`' + '\n '
        else: 
            command = self.bot.get_command(help_command)
            aliases = ""
            for alias in command.aliases: 
                aliases += "`" + alias + "`" 
            emb.title =':notebook_with_decorative_cover: ' + '`' + command.name + '`'
            emb.add_field(name="Usage", value="`" + self.bot.command_prefix[0] + f'{command.name} {command.signature}' + "`", inline=True)
            emb.add_field(name="Aliases", value=aliases, inline=True)
            emb.add_field(name="Description", value=command.brief, inline=False)

        return await ctx.send(embed=emb)
        
