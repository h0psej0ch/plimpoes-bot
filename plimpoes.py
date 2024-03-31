import os
import time
import datetime
import asyncio
import functools
import itertools
import math
import random
import json
import discord
import yt_dlp
import praw
import urllib.request
from dotenv import load_dotenv
from datetime import timedelta
from filelock import FileLock
from discord.ui import Button, View
from async_timeout import timeout
from discord.ext import commands
from discord.ext import tasks

# Silence useless bug reports messages
yt_dlp.utils.bug_reports_message = lambda: ""

load_dotenv("API.env")

#plimpoes
#token = os.getenv("PLIMPOES")

#testbot
token = os.getenv('TESTBOT')
canvastoken = os.getenv('CANVAS')

print(token)
print(canvastoken)
#Testing fakedata
assUrlList = ['wowwieee its a link']

# Actual data
# assUrlList = [
#     'https://canvas.utwente.nl/api/v1/courses/14218/assignments?access_token=',
#     'https://canvas.utwente.nl/api/v1/courses/14555/assignments?access_token='
# ]
weekMessage = False

reddit = praw.Reddit(
    client_id="cuwiAvqyieMfEQ",
    client_secret="SOVBtKKEYaz90mYGdeEDo_jRh2AueA",
    username="TacoDCBot",
    password="TacoDCBot",
    user_agent="bruh",
)

First = True
global chan
chan = None

pingid = 1185599761173188682
musicpoesidlist = []
assignmentpoesidlist = []

assignment_json = 'data.json'

with open(assignment_json, 'r') as f:
    assData = json.load(f)

# format: [[(AssignmentName, AssignmentDueDate), (AssignmentName, AssignmentDueDate), ...], [(24hour, 1hour), (24hour, 1hour), ...]]
assignmentlist = [[], []]

plimpoesEmbed = discord.Embed(title="plimpoes", colour=0x7F684F)
plimpoesEmbed.set_image(
    url="https://media.discordapp.net/stickers/1062405909910933565.webp?size=160"
)

commandlist = [
    "join",
    "leave",
    "loop",
    "now",
    "pause",
    "play",
    "queue",
    "remove",
    "resume",
    "skip",
    "stop",
    "summon",
    "volume",
]


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",
    }

    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(
        self,
        ctx: commands.Context,
        source: discord.FFmpegPCMAudio,
        *,
        data: dict,
        volume: float = 0.5,
    ):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get("upload_date")
        self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        self.title = data.get("title")
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.duration = self.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

    def __str__(self):
        return "**{0.title}** by **{0.uploader}**".format(self)

    @classmethod
    async def create_source(
        cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None
    ):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            cls.ytdl.extract_info, search, download=False, process=False
        )
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError("Couldn't find anything that matches `{}`".format(search))
            time.sleep(3)
            await chan.purge(limit=1)

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(
                    "Couldn't find anything that matches `{}`".format(search)
                )
                time.sleep(3)
                await chan.purge(limit=1)

        webpage_url = process_info["webpage_url"]
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError("Couldn't fetch `{}`".format(webpage_url))
            time.sleep(3)
            await chan.purge(limit=1)

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"].pop(0)
                except IndexError:
                    raise YTDLError(
                        "Couldn't retrieve any matches for `{}`".format(webpage_url)
                    )
                    time.sleep(3)
                    await chan.purge(limit=1)

        return cls(
            ctx, discord.FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS), data=info
        )

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append("{} days".format(days))
        if hours > 0:
            duration.append("{} hours".format(hours))
        if minutes > 0:
            duration.append("{} minutes".format(minutes))
        if seconds > 0:
            duration.append("{} seconds".format(seconds))

        return ", ".join(duration)


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        try:
            embed = (
                discord.Embed(
                    title="Now playing",
                    description="```css\n{0.source.title}\n```".format(self),
                    color=0x7F684F,
                )
                .add_field(name="Duration", value=self.source.duration)
                .add_field(name="Requested by", value=self.requester.mention)
                .add_field(
                    name="Uploader",
                    value="[{0.source.uploader}]({0.source.uploader_url})".format(self),
                )
                .add_field(name="URL", value="[Click]({0.source.url})".format(self))
                .set_thumbnail(url=self.source.thumbnail)
            )

            return embed
        except:
            print("fuck you")


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                global playembed
                await playembed.delete()
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            try:
                await playembed.edit(embed=self.current.create_embed())
                print("edited")
            except:
                playembed = await self.current.source.channel.send(
                    embed=self.current.create_embed()
                )
                print("created")

            page = 1
            items_per_page = 10
            pages = math.ceil(len(self.songs) / items_per_page)

            start = (page - 1) * items_per_page
            end = start + items_per_page

            queue = ""
            for i, song in enumerate(self.songs[start:end], start=start):
                queue += "`{0}.` [**{1.source.title}**]({1.source.url})\n".format(
                    i + 1, song
                )

            embed = discord.Embed(
                color=0x7F684F,
                description="**{} tracks:**\n\n{}".format(len(self.songs), queue),
            ).set_footer(text="Viewing page {}/{}".format(page, pages))
            global chan
            global queueembed
            try:
                await queueembed.edit(embed=embed)
            except:
                queueembed = await chan.send(embed=embed)
                return queueembed, playembed

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage(
                "This command can't be used in DM channels."
            )

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    # async def cog_command_error(self, ctx: commands.Context,
    #                             error: commands.CommandError):
    #     # await ctx.send('An error occurred: {}'.format(str(error)))
    #     time.sleep(3)
    #     # await chan.purge(limit=1)

    @commands.command(name="join", invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name="summon")
    @commands.has_permissions(manage_guild=True)
    async def _summon(
        self, ctx: commands.Context, *, channel: discord.VoiceChannel = None
    ):
        """Summons the bot to a voice channel.

        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError(
                "You are neither connected to a voice channel nor specified a channel to join."
            )
            time.sleep(3)
            await chan.purge(limit=1)

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name="leave", aliases=["disconnect"])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            await ctx.send("Not connected to any voice channel.")
            time.sleep(3)
            await chan.purge(limit=1)
            return

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

        global playembed
        global queueembed
        try:
            await playembed.delete()
            await queueembed.delete()
        except:
            print("naha")

    @commands.command(name="volume")
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send("Nothing being played at the moment.")

        if 0 > volume > 100:
            return await ctx.send("Volume must be between 0 and 100")

        ctx.voice_state.volume = volume / 100
        await ctx.send("Volume of the player set to {}%".format(volume))

    @commands.command(name="now", aliases=["current", "playing"])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""
        await ctx.invoke(self._queue)
        global playembed
        try:
            await playembed.edit(embed=self.current.create_embed())
            print("edited")
        except:
            playembed = await self.current.source.channel.send(
                embed=self.current.create_embed()
            )
            print("created")

    @commands.command(name="pause")
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()

    @commands.command(name="resume")
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()

    @commands.command(name="stop")
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
        global playembed
        global queueembed
        try:
            await playembed.delete()
            await queueembed.delete()
        except:
            print("naha")

    @commands.command(name="skip")
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send("Not playing any music right now...")

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            ctx.voice_state.skip()
            await ctx.invoke(self._queue)

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                ctx.voice_state.skip()
                await ctx.invoke(self._queue)
            else:
                await ctx.send(
                    "Skip vote added, currently at **{}/3**".format(total_votes)
                )

        else:
            await ctx.send("You have already voted to skip this song.")

    @commands.command(name="queue")
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.

        You can optionally specify the page to show. Each page contains 10 elements.
        """

        # if len(ctx.voice_state.songs) == 0:
        #     return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ""
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += "`{0}.` [**{1.source.title}**]({1.source.url})\n".format(
                i + 1, song
            )
        embed = discord.Embed(
            color=0x7F684F,
            description="**{} tracks:**\n\n{}".format(
                len(ctx.voice_state.songs), queue
            ),
        ).set_footer(text="Viewing page {}/{}".format(page, pages))
        global chan
        global queueembed
        try:
            await queueembed.edit(embed=embed)
        except:
            queueembed = await chan.send(embed=embed)
            return queueembed

    @commands.command(name="shuffle")
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("Empty queue.")

        ctx.voice_state.songs.shuffle()

    @commands.command(name="remove")
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("Empty queue.")

        ctx.voice_state.songs.remove(index - 1)
        await ctx.invoke(self._queue)

    @commands.command(name="loop")
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.

        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send("Nothing being played at the moment.")

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop

    @commands.command(name="play")
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        # if not ctx.voice_state.voice:
        #     print(ctx.voice_state.voice)
        #     await ctx.invoke(self._join)
        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send(
                    "An error occurred while processing this request: {}".format(str(e))
                )
                time.sleep(3)
                await chan.purge(limit=1)
            else:
                song = Song(source)
                await ctx.invoke(self._queue)
                await ctx.voice_state.songs.put(song)
                await ctx.invoke(self._queue)
                # global playembed
                # try:
                #   await playembed.edit(embed=self.current.create_embed())
                #   print("edited")
                # except:
                #   playembed = await ctx.channel.send(embed=Song.create_embed())
                #   print("created")

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError("You are not connected to any voice channel.")
            time.sleep(3)
            await chan.purge(limit=1)

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError("Bot is already in a voice channel.")
                time.sleep(3)
                await chan.purge(limit=1)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot("", description="plimpoes", intents=intents)


@bot.event
async def on_ready():
    global guild
    global role

    # Actual server
    #guild = bot.get_guild(1175750255808094220)

    # Test server
    guild = bot.get_guild(1072906075373834250)

    
    await bot.add_cog(Music(bot))
    try:
        synced = await bot.tree.sync()
        print("succeed " + str(len(synced)))
    except:
        print("failed")
    assignmentcheck.start()
    print(f"Logged on as {bot.user}! (ID: {bot.user.id})")
    role = discord.utils.get(guild.roles, name="assignments ping")


@bot.command()
async def hello(ctx):
    msg = f"Hi{ctx.author.mention}"
    await ctx.send(msg)


@tasks.loop(seconds=60)
async def assignmentcheck():
    global role
    global weekMessage
    global assUrlList
    global assData  

    print("Checking assignments")

    currentday = datetime.datetime.now() + timedelta(hours=1)
    for url in assUrlList:

        # response = urllib.request.urlopen(url + canvastoken)
        # data = response.read().decode("utf-8", "ignore")
        # data = json.loads(data)

        courseresponse = urllib.request.urlopen(' https://canvas.utwente.nl/api/v1/courses' + '?access_token=' + canvastoken)
        coursedata = courseresponse.read().decode("utf-8", "ignore")
        coursedata = json.loads(coursedata)

        with open('course.json', 'w') as f:
            json.dump(coursedata, f)
            f.flush()
            os.fsync(f.fileno())

        with open('fakedata.json', 'r') as fake:
            data = json.load(fake)

            edited = False

            with open("yes.json", "w") as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())

            for i in data:
                due = i["due_at"]
                assname = i["name"]
                hurl = i["html_url"]

                if due is not None:
                    date, time = due.split("T")
                    time = time[:-1]
                    date = date.split("-")
                    time = time.split(":")
                    assignmentdaytime = datetime.datetime(
                        int(date[0]),
                        int(date[1]),
                        int(date[2]),
                        (int(time[0]) + 1) % 24,
                        int(time[1]),
                        int(time[2]),
                    )

                    for course in coursedata:
                        if course["id"] == i["course_id"]:
                            courseName = course["name"]
                            break

                    try:
                        for channel in assData["data"]:
                            print(channel)
                            chan = bot.get_channel(int(channel))
                            print("Now doing " + str(chan.name))
                            if currentday <= assignmentdaytime:
                                if assname not in assData["data"][channel]: # The assignment is new and is to be added
                                    await assignmentSend(chan, assname, assignmentdaytime, hurl, 0, courseName)
                                    
                                elif ("24hour" not in assData["data"][channel][assname] and (assignmentdaytime - currentday).days == 0
                                and "1hour" not in assData["data"][channel][assname]): # Assignment is due in 24 hours
                                    await assignmentSend(chan, assname, assignmentdaytime, hurl, 1, courseName)

                                elif ("1hour" not in assData["data"][channel][assname]
                                and (assignmentdaytime - currentday).days == 0
                                and (assignmentdaytime - currentday).seconds < 3600): # Assignment is due in 1 hour
                                    await assignmentSend(chan, assname, assignmentdaytime, hurl, 2, courseName)

                            elif assname in assData["data"][channel]: # Assignment is overdue but still in the list huh?
                                print("Assignment overdue")
                                try:
                                    for timeslot, message in assData["data"][channel][assname].items():
                                        message = await chan.fetch_message(message)
                                        await message.delete()
                                except:
                                    print("An error occurred while deleting the message")
                                print(assData["data"][channel][assname])
                                assData["data"][channel].pop(assname)
                                edited = True

                        if edited:
                            print("Saving the data")
                            with open(assignment_json, 'w') as f:
                                json.dump(assData, f)
                                f.flush()
                                os.fsync(f.fileno())

                    except Exception as e:
                        print(f"An error occurred: {e}, {assname}")
                        
async def assignmentSend(chan, assname, assignmentdaytime, hurl, index, coursename):
    global role

    match index:
        case 0: 
            title = "New assignment created!"
        case 1:
            title = "Assignment due in 24 hours!"
        case 2:
            title = "Assignment due in 1 hour!"

    assignmentembed = discord.Embed(
        title=title,
        colour=0x7F684F,
        description=role.mention,
        url = hurl
    )
    assignmentembed.add_field(name="Assignment name", value=assname)
    assignmentembed.add_field(name="Due date", value=assignmentdaytime)
    assignmentembed.add_field(name="Course", value=coursename)
    await chan.send(embed=assignmentembed)



@bot.event
async def on_message(message):
    global musicpoesidlist
    global chan
    global assData 
    print(message.channel)
    print(f"Message from {message.author}: {message.content}")
    if message.author != bot.user:
        if "this channel" in message.content:
            musicpoesid = message.channel.id
            musicpoesidlist.append(musicpoesid)
            chan = bot.get_channel(musicpoesid)
            await chan.purge()
            await chan.send(embed=plimpoesEmbed)
            return
        elif "this assignment channel" in message.content:
            if str(message.channel.id) not in assData["data"]:
                assData["data"][message.channel.id] = {}
                chan = bot.get_channel(message.channel.id)
                await chan.purge()
                await chan.send(embed=plimpoesEmbed)
                print("The whole list: " + str(assignmentlist))
                for assignment in assignmentlist[0]:
                    assData["data"][message.channel.id][assignment[0].strip()] = {"initial": None, "24hour": None, "1hour": None}
                    #TODO add the sending of the messages
            else:
                chan = bot.get_channel(message.channel.id)
                print("purging")
                await chan.purge()
                return
            
            with open(assignment_json, "w") as f:
                json.dump(assData, f)
                f.flush()
                os.fsync(f.fileno())

        if str(message.channel) == "plimpoes-appreciation-channel":
            await message.channel.send(embed=plimpoesEmbed)
        elif message.channel.id in musicpoesidlist:
            musicpoesid = message.channel.id
            chan = bot.get_channel(musicpoesid)
            await chan.purge(limit=1)
            found = False
            for command in commandlist:
                if command in message.content:
                    await bot.process_commands(message)
                    found = True
            if found == False:
                message.content = "play " + str(message.content)
                await bot.process_commands(message)

    elif message.author == bot.user:
        print("FOUND A BOT MESSAGE AAAAAAAAAA")   
        print(message.channel.id)
        print(assData)
        print("\n")
        if str(message.channel.id) in assData["data"]:
            print(message.embeds[0].fields[0].value)
            match message.embeds[0].title:
                case "New assignment created!" | "Current assignment!":
                    assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()] = {}
                    assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()]["initial"] = message.id
                    print("New assignment created")
                case "Assignment due in 24 hours!":
                    assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()]["24hour"] = message.id
                    delete_message = await message.channel.fetch_message(assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()]["initial"])
                    await delete_message.delete()
                    assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()].pop("initial")
                    print("24 hours left")
                case "Assignment due in 1 hour!":
                    assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()]["1hour"] = message.id
                    delete_message = await message.channel.fetch_message(assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()]["24hour"])
                    await delete_message.delete()
                    assData["data"][str(message.channel.id)][message.embeds[0].fields[0].value.strip()].pop("24hour")
                    print("1 hour left")
            print("New bot message: " + str(message.embeds))

        with open(assignment_json, "w") as f:
            json.dump(assData, f)
            f.flush()
            os.fsync(f.fileno())

    return First


@bot.tree.command(
    name="plimpoes", description="Rates how much plimpoes you are :hot_face:"
)
async def plimpoes(interaction: discord.Interaction):
    plimprate = str(random.randint(0, 10)) + "/10 plimpoes"
    print(plimprate)
    plimprateEmbed = discord.Embed(title=plimprate, colour=0x7F684F)
    plimprateEmbed.set_image(
        url="https://media.discordapp.net/stickers/1062405909910933565.webp?size=160"
    )
    await interaction.response.send_message(embed=plimprateEmbed)


@bot.tree.command(name="foodporn", description="Gib foodporn")
async def foodporn(interaction: discord.Interaction):
    subredditfood = reddit.subreddit("foodporn")
    all_subs = []
    top = subredditfood.top(limit=50)
    for submission in top:
        all_subs.append(submission)

    random_sub_food = random.choice(all_subs)

    Food_Name = random_sub_food.title
    Food_Url = random_sub_food.url

    FoodEmbed = discord.Embed(title=Food_Name, colour=0x7F684F)

    FoodEmbed.set_image(url=Food_Url)

    await interaction.response.send_message(embed=FoodEmbed)

@bot.tree.command(name="liquid", description="Gib very liquid cat")
async def liquid(interaction: discord.Interaction):
    await cat(interaction)

async def cat(interaction: discord.Interaction):
    try:
        found = False
        while not found:
            found = True
            # Get a random post from the subreddit and decode
            subredditcat = reddit.subreddit("catsareliquid").random()
            while subredditcat.author is None or not subredditcat.is_robot_indexable:
                subredditcat = reddit.subreddit("catsareliquid").random()
            Cat_Name = subredditcat.title
            Cat_Url = subredditcat.url
            Cat_Permalink = subredditcat.permalink

            print("https://reddit.com" + Cat_Permalink)

            # Get the json of the post
            response = urllib.request.urlopen("https://reddit.com" + Cat_Permalink + ".json")
            data = response.read().decode('utf-8', 'ignore')
            data = json.loads(data)

            # Checking for crosspost
            if "crosspost_parent_list" in data[0]["data"]["children"][0]["data"]:
                data = data[0]["data"]["children"][0]["data"]["crosspost_parent_list"][0]
                if data["author"] == "[deleted]" or not data["is_robot_indexable"]:
                    found = False
            else:
                data = data[0]["data"]["children"][0]["data"]

        # Checking for a video, if so reply with the video
        if data["secure_media"] != None:
            video_url = data["secure_media"]["reddit_video"]["fallback_url"]

            print(video_url)

            await interaction.response.send_message(content=("[" + Cat_Name + "](<https://reddit.com" + Cat_Permalink + ">)"))

            with open("video.mp4","wb") as f:
                g = urllib.request.urlopen(video_url)
                f.write(g.read())

            print("video downloaded")

            with open ("video.mp4", "rb") as f:
                i = 0
                while i < 10:
                    print("sending video")
                    i += 1
                    await interaction.channel.send(file=discord.File(f))
                    break
                

        # If it's not a video, send the image in a embed
        elif "media_metadata" in data:
            links = [data["media_metadata"][x]["s"]["u"] for x in data["media_metadata"]]
            print(links)
            for i in range(len(links)):
                if links[i].startswith("https://preview.redd.it"):
                    links[i] = links[i].replace("preview", "i")
            print(links)
            Embed_List = []
            for link in links:
                CatEmbed = discord.Embed(title=Cat_Name, colour=0x7F684F, url=Cat_Url)
                CatEmbed.set_image(url=link)
                Embed_List.append(CatEmbed)
            await interaction.response.send_message(embeds=Embed_List)
        else:
            CatEmbed = discord.Embed(title=Cat_Name, colour=0x7F684F, url="https://reddit.com" + Cat_Permalink)
            CatEmbed.set_image(url=Cat_Url)
            await interaction.response.send_message(embed=CatEmbed)
    except Exception as e:
        print("invalid post")
        print(e)

        Repeat = Button(label = "Try again", style = discord.ButtonStyle.primary)
        Repeat.callback = cat
        view = View()
        view.add_item(Repeat)

        await interaction.response.send_message("I failed to get a liquid cat, sorry :(", ephemeral=True, view = view)

async def button_callback(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await cat(ctx)

bot.run(token)