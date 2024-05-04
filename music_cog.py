import discord
from discord.ext import commands
from discord.ext import tasks
from discord.ui import Button, View
import json
import asyncio
import datetime
import os
import yt_dlp

class music_cog(commands.Cog):
    def __init__(self, botImport: commands.Bot):
        self.bot = botImport
        self.musicQueue = []
        self.playing = False
        self.vc = None
        self.start = datetime.datetime.now()

        self.invisible_char = " "

        self.YTDL_OPTIONS = {
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

        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 30",
            "options": "-vn",
        }

        self.ytdl = yt_dlp.YoutubeDL(self.YTDL_OPTIONS)

        self.commandlist = [
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
            "setup",
        ]

        print(f"Bot instance in MyCog: {self.bot}")

    @commands.command(name="join", description="Joins the voice channel")
    async def join(self, ctx):
        if (ctx.author.voice):
            channel = ctx.author.voice.channel
            self.vc = await channel.connect()
            self.vc.play(discord.FFmpegPCMAudio(source="hema.mp3", options = self.FFMPEG_OPTIONS))

    async def turntable(self, ctx):
        song = self.musicQueue.pop(0)
        self.vc.play(discord.FFmpegPCMAudio(executable="C:/Users/T Bot/Downloads/ffmpeg-7.0-full_build/bin/ffmpeg.exe", source=song[0], options=self.FFMPEG_OPTIONS), 
                     after=lambda e: asyncio.run_coroutine_threadsafe(self.nextSong(ctx, e), self.bot.loop))
        self.start = datetime.datetime.now()

    async def editEmbed(self, ctx, song):
        # Chaning the embed
        self.musicEmbed.set_field_at(0, name="Artist", value = song[2])
        self.musicEmbed.set_field_at(1, name="Length", value = song[3])
        self.musicEmbed.set_field_at(2, name="Queue Length", value = str(len(self.musicQueue)))
        self.musicEmbed.url = song[0]
        self.musicEmbed.title = ":dvd: " + song[1] + " :dvd:"
        await self.player.edit(embed=self.musicEmbed)

        return
    
    async def updateQueueEmbed(self, ctx):
        self.musicEmbed.set_field_at(2, name="Queue Length", value = str(len(self.musicQueue)))
        await self.player.edit(embed=self.musicEmbed)

    async def nextSong(self, ctx, error = None):
        print((datetime.datetime.now() - self.start).total_seconds())
        if self.musicQueue != []:
            self.playing = True
            await self.editEmbed(ctx, self.musicQueue[0])
            await self.turntable(ctx)
        else: 
            await self.vc.disconnect()
            self.vc = None
            self.playing = False
    
    def getUrl(self, song):
        info = self.ytdl.extract_info(song, download=False)
        with open("info.json", 'w') as f:
            json.dump(info, f)
            f.flush()
            os.fsync(f.fileno())
        return [info["entries"][0]["url"], info["entries"][0]["title"], info["entries"][0]["uploader"], info["entries"][0]["duration"]]

    @commands.command(name = "play", description = "Plays a song")
    async def play(self, ctx, *args):
        if ctx.author.voice == None:
            await ctx.send(content = "You must be in a voice channel to use this command")
            return
        if self.vc == None or self.vc.channel != ctx.author.voice.channel:
            self.vc = await ctx.author.voice.channel.connect()
        argsString = " ".join(args)
        print(argsString)
        await ctx.send(content = "play " + argsString)
        self.musicQueue.append(self.getUrl(argsString))
        await self.updateQueueEmbed(ctx)
        print(self.playing)
        if self.playing == False:
            print("Still doing this fuck you!")
            await self.nextSong(ctx)

    @commands.command(name = "skip", description = "Skips the current song")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.send_message("Skipped", ephemeral=True, delete_after=5)

    @commands.command(name="setup", description="Sets up the channel")
    async def setup(self, ctx):
        self.musicpoesid = ctx.channel.id
        await ctx.channel.purge()
        #await ctx.send(embed=plimpoesEmbed)

        self.musicEmbed = discord.Embed(
            title = ":dvd: Currently inactive :dvd:",
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            colour = 0x7F684F
        )
        self.musicEmbed.set_thumbnail(url="https://i.ytimg.com/vi/gG_dA32oH44/maxresdefault.jpg")
        self.musicEmbed.add_field(name="Artist", value = "-")
        self.musicEmbed.add_field(name="Length", value = "-")
        self.musicEmbed.add_field(name="Queue Length", value = "0")

        skipButton = Button(style=discord.ButtonStyle.primary, label=">>")
        skipButton.callback = self.skip
        view = View()
        view.add_item(skipButton)

        self.player = await ctx.send(embed=self.musicEmbed, view=view)

    @commands.command(name="MUSIC", description="processes music commands")
    async def music(self, ctx):
        if ctx.message.content.startswith("MUSIC setup"):
            await self.setup(ctx)
        
        elif ctx.channel.id == self.musicpoesid:
            if ctx.message.content.split(" ")[1] in self.commandlist:
                ctx.message.content = ctx.message.content.replace("MUSIC ", "")
                print(ctx.message.content)
                await self.bot.process_commands(ctx.message)
            else:
                ctx.message.content = ctx.message.content.replace("MUSIC", "play")
                print(ctx.message.content)
                await self.bot.process_commands(ctx.message)
            
    
    