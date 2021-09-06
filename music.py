import discord
import wavelink
import asyncio

from discord import Embed
from discord.ext import commands
from enum import Enum
from globals import GLOBAL_NAME

class State(Enum):
    IDLE = 0
    PLAY_LOOP = 1
    LOOP_SINGLE = 2
    
class Music(commands.Cog):

    def __init__(self, bot):
        self.state = State.IDLE
        self.bot = bot
        self.queue = []
        self.track_finished = asyncio.Event()
        self.cur_track = None
        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot=self.bot)
        self.bot.loop.create_task(self.start_nodes())
    async def on_disconnect(self):
        print("disconnected")
        
    async def start_nodes(self):
        await self.bot.wait_until_ready()
        node = await self.bot.wavelink.initiate_node(host='127.0.0.1',
                                            port=2333,
                                            rest_uri='http://127.0.0.1:2333',
                                            password='youshallnotpass',
                                            identifier='TEST',
                                            region='us_west')
        node.set_hook(self.on_event_hook)

    async def play_loop(self, ctx):
        await ctx.send(f'Debug: reached play loop')
        self.track_finished.clear()
        track = self.queue[0]
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            await ctx.invoke(self.connect)

        await ctx.send(f'Now playing {str(track)}.')
        await player.play(track)
        await self.track_finished.wait()
        if self.state == State.PLAY_LOOP: 
            del self.queue[0]
        self.bot.loop.create_task(self.play_loop(ctx))

    async def on_event_hook(self, event):
        if isinstance(event, (wavelink.TrackEnd)):
            self.track_finished.set()    

    @commands.command(name='connect', aliases=['c'], brief=f'Connects {GLOBAL_NAME} to the specified voice channel.')
    async def connect(self, ctx, *, channel: discord.VoiceChannel=None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

        player = self.bot.wavelink.get_player(ctx.guild.id)
        await ctx.send(f'Connecting to **`#{channel.name}`**')
        await player.connect(channel.id)

    @commands.command(name='disconnect', aliases=['leave', 'x'], brief=f'Disconnects {GLOBAL_NAME} from the current voice channel.')
    async def disconnect(self, ctx):
        self.state = State.IDLE
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if player:
            await player.stop()
            await player.disconnect()
            await player.destroy()
            
    @commands.command(name='play',  aliases=['p'], brief=f'Searches for the given track name with the specified source and plays the first result in the voice channel you are in, adding it to the queue. You must be in a voice channel to use this command.')
    async def play(self, ctx, *, query: str):
        print(query)
        self.track_finished.clear()
        self.cur_ctx = ctx
        tracks = await self.bot.wavelink.get_tracks(f'ytsearch:{query}')
        if not tracks:
            return await ctx.send('Could not find any songs with that query.')

        self.queue.append(tracks[0])
        await ctx.send(f'Added {tracks[0].title} to the queue.')
        if self.state == State.IDLE:
            self.state = State.PLAY_LOOP
            self.bot.loop.create_task(self.play_loop(ctx)) 

    @commands.command(name='list',  aliases=['q'], brief=f'Lists the tracks in the queue.')
    async def list(self, ctx):
        emb = Embed(
            title="Queue",
            author="Wobot",
            description=""
        )
        for index, elem in enumerate(self.queue):
            print(elem.title)
            emb.description += f'**{str(index + 1)}.** [{elem.title}]({elem.uri})\n'
        return await ctx.send(embed=emb)


    @commands.command(name='loop',  aliases=['l'], brief=f'Toggles looping the current track forever, overriding the queue. `<toggle>` must be either `on` or `off`.')
    async def loop(self, ctx, toggle):
        if self.state == State.PLAY_LOOP:
            if toggle == "on":
                self.state = State.LOOP_SINGLE 
        elif self.state == State.LOOP_SINGLE: 
            if toggle == "off": 
                self.state = State.PLAY_LOOP

    @commands.command(name='pause',  aliases=['e'], brief=f'Pauses the current track.')
    async def pause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        await player.set_pause(True)

    @commands.command(name='resume', aliases=['r'], brief=f'Resumes playing the current track.')
    async def resume(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        await player.set_pause(False)

