from discord.ext import commands
from music import Music
from error import ErrorHandler
from help import Help

class Bot(commands.Bot):
    def __init__(self):
        super(Bot,self).__init__(command_prefix=['!', 'wobot '], help_command=None)
        self.remove_command("help")
        self.add_cog(Music(self))
        self.add_cog(ErrorHandler(self))
        self.add_cog(Help(self))
        
    async def on_ready(self):
        print(f'Logged in as {self.user.name} | {self.user.id}')
 
bot = Bot()
token = open("key.txt", 'r').read()
bot.run(token)
