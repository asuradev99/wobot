import discord
import wavelink
import asyncio
import random 

from discord import Embed
from discord.ext import tasks, commands
from discord.utils import get

from enum import Enum
from globals import GLOBAL_NAME
import datetime


class State(Enum):
    IDLE = 0
    PLAY_LOOP = 1
    LOOP_SINGLE = 2
    QUEUE_LOOP = 3


class Music(commands.Cog):

    def __init__(self, bot):
        self.state = State.IDLE
        self.bot = bot
        self.queue = []
        self.track_finished = asyncio.Event()
        self.djon = False
        self.dj_role = None
        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot=self.bot)
        self.bot.loop.create_task(self.start_nodes())

    def parse_flags(self, flags: str):
        return list(flags)
    def check_dj(self, ctx):
        if self.dj_role == None or not self.djon: 
            return
        if not ctx.message.guild.get_role(self.dj_role) in ctx.message.author.roles:
            raise discord.DiscordException('You currently do not have permission to use this command, as the bot is in DJ mode.')
    async def on_disconnect(self):
        print("disconnected")

    async def confirm(self, ctx):
        await ctx.message.add_reaction(emoji="\u2705")
    async def start_nodes(self):
        await self.bot.wait_until_ready()
        node = await self.bot.wavelink.initiate_node(host='127.0.0.1',
                                                     port=2333,
                                                     rest_uri='http://127.0.0.1:2333',
                                                     password='youshallnotpass',
                                                     identifier='TEST',
                                                     region='us_west')
        node.set_hook(self.on_event_hook)
    
    async def play_loop(self, ctx, pos=0):
        self.track_finished.clear()
        if len(self.queue) == 0:
            self.state = State.IDLE
            return
        track = self.queue[0]
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            try:
                await ctx.invoke(self.connect)
            except discord.DiscordException as e: 
                self.state = State.IDLE
                raise discord.DiscordException(str(e))
       
        embed = discord.Embed(title="**Now playing**",
                              description=f"**[{track.title}]({track.uri})**"
                              )
        embed.set_thumbnail(url=track.thumb)
        embed.add_field(name="Uploader", value=track.author, inline=True)
        time_mil = track.duration
        seconds=time_mil/1000
        embed.add_field(name="Duration", value=str(datetime.timedelta(seconds=seconds)), inline=True)
        await ctx.send(embed=embed)
        await player.play(track=track, replace=False) 
        await player.seek(pos)
        await self.track_finished.wait()
        if self.state != State.LOOP_SINGLE:
            if self.state == State.QUEUE_LOOP: 
                self.queue.append(track)
            del self.queue[0]
        
        print("next song")
        self.bot.loop.create_task(self.play_loop(ctx))

    async def on_event_hook(self, event):
        if isinstance(event, (wavelink.TrackEnd)):
            print(event.reason)
            if event.reason == "FINISHED":
                self.track_finished.set()

    @commands.command(name='connect', aliases=['c'], brief=f'Connects {GLOBAL_NAME} to the specified voice channel.')
    async def connect(self, ctx, *, channel: discord.VoiceChannel = None):
        self.check_dj(ctx)
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise discord.DiscordException(
                    'No channel to join. Please either specify a valid channel or join one.')
        if player.is_playing: 

            print(str(player.is_playing) + str(self.state))
            pos = player.position
            await ctx.invoke(self.disconnect)
            await player.connect(channel.id)
            self.bot.loop.create_task(self.play_loop(ctx, pos=pos))
        else:
            await player.connect(channel.id)
        await self.confirm(ctx)

    @commands.command(name='disconnect', aliases=['leave', 'x'], brief=f'Disconnects {GLOBAL_NAME} from the current voice channel.')
    async def disconnect(self, ctx):
        self.check_dj(ctx)
        self.state = State.IDLE
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if player:
            await player.stop()
            for task in list(asyncio.all_tasks()):
                if "Music.play_loop" in str(task.get_coro()):
                    print("canceling")
                    task.cancel()
            await player.disconnect()
            await player.destroy()

    @commands.command(name='play',  aliases=['p'], brief=f'Searches for the given track name with the specified source and plays the first result in the voice channel you are in, adding it to the queue. You must be in a voice channel to use this command.')
    async def play(self, ctx, *, query: str):        
        self.bot.loop.create_task(self.query(ctx, query))

    async def query(self, ctx, query: str):
        self.track_finished.clear()
        self.cur_ctx = ctx
        tracks = await self.bot.wavelink.get_tracks(f'ytsearch:{query}')
        if not tracks:
            embed=discord.Embed(description="I could not find any songs with that query.")
            await ctx.send(embed=embed)
            return
        self.queue.append(tracks[0])

        if self.state != State.IDLE:
            embed = discord.Embed(title=f"**{tracks[0].title}**",
                                description="This track has been added to the queue.",
                                url=tracks[0].uri
                                )
            embed.set_thumbnail(url=tracks[0].thumb)
            embed.add_field(name="Uploader", value=tracks[0].author, inline=True)
            time_mil = tracks[0].duration
            seconds=time_mil/1000
            embed.add_field(name="Duration", value=str(datetime.timedelta(seconds=seconds)), inline=True)
            await ctx.send(embed=embed)
        else:
            self.state = State.PLAY_LOOP
            self.bot.loop.create_task(self.play_loop(ctx))

    @commands.command(name='list',  aliases=['q'], brief=f'Lists the tracks in the queue.', description="`-s`: Shuffles the queue.\n`-c`: Clears the queue.")
    async def list(self, ctx, flags=""):
        l_opt = self.parse_flags(flags) 
            
        emb = Embed(
            title="Queue",
            author="Wobot",
            description=""
        )
        if "s" in l_opt:
            self.check_dj(ctx)
            random.shuffle(self.queue)
            emb.description += "The queue has been shuffled.\n"
        if (len(self.queue) == 0):
            emb.description += "The queue is currently empty."
        for index, elem in enumerate(self.queue):
            emb.description += f'**{str(index + 1)}.** [{elem.title}]({elem.uri})\n'
        
        if "c" in l_opt: 
            self.check_dj(ctx)
            self.queue.clear()
            emb.description = "The queue has been cleared.\n"

        
        footer_text = {
            State.PLAY_LOOP : "Playing queue",
            State.QUEUE_LOOP : "Looping queue",
            State.LOOP_SINGLE : "Looping track ",
            State.IDLE : "Idle"
        }
        
        emb.set_footer(text="\n Current Mode: " + footer_text[self.state])
        return await ctx.send(embed=emb)

    @commands.command(name='loop',  aliases=['l'], brief=f'Toggles looping the current track forever, overriding the queue. `<toggle>` must be either `on` or `off`.', description="`-q`: Toggle the queue loop (loops over the entire queue) instead.")
    async def loop(self, ctx, toggle, flags=[]):
        self.check_dj(ctx)
        l_opt = self.parse_flags(flags) 
        target_state = State.QUEUE_LOOP if 'q' in l_opt else State.LOOP_SINGLE
        print(l_opt)
        if toggle == "on":
            self.state = target_state
    
        if toggle == "off":
            self.state = State.PLAY_LOOP
        print(self.state)
    
    @commands.command(name='skip',  aliases=['s'], brief='Skips the track that is currently playing.')
    async def skip(self, ctx, num = 1):
        self.check_dj(ctx)
        print("0")
        if len(self.queue) == 0:
            return
        player = self.bot.wavelink.get_player(ctx.guild.id)
        num = min(num, len(self.queue))      
           
        for _ in range(num):
            print(self.state)
            if(self.state == State.QUEUE_LOOP):
                self.queue.append(self.queue[0])
            if(self.state != State.LOOP_SINGLE):
                print("deleting thing 0 " + self.queue[0].title)
                del self.queue[0]
        await player.stop()   
        for task in list(asyncio.all_tasks()):
            if "Music.play_loop" in str(task.get_coro()):
                print("canceling")
                task.cancel()
                self.bot.loop.create_task(self.play_loop(ctx))
                break

    @commands.command(name='pause',  aliases=['e'], brief=f'Pauses the current track.')
    async def pause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        await player.set_pause(True)

    @commands.command(name='resume', aliases=['r'], brief=f'Resumes playing the current track.')
    async def resume(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id)
        await player.set_pause(False)

    @commands.has_permissions(manage_roles=False)
    @commands.command(name='dj', aliases=[''], brief=f'Sets a DJ role for the bot, or toggles DJ mode. It can also be used to set the dj role. `<toggle>` must be either the dj role you want to set, (eg. @<role-name>), or `on` or `off`.')
    async def dj(self, ctx, toggle):
        if toggle == "off":
            self.djon = False
        elif toggle == "on":
            self.djon = True
        else: 
            self.dj_role = int(toggle[3:-1])
        
        
