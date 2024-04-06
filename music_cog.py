import discord
from discord.ext import commands
from discord.ext import tasks
from discord.ui import Button, View
import json
import os
import yt_dlp

class music_cog(commands.Cog):
    def __init__(self, botImport: commands.Bot):
        self.bot = botImport
        self.musicQueue = []
        self.playing = False
        self.vc = None

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

        print(f"Bot instance in MyCog: {self.bot}")

    @commands.command(name="joinpwease", description="Joins the voice channel")
    async def joinpwease(self, ctx):
        if (ctx.author.voice):
            channel = ctx.author.voice.channel
            self.vc = await channel.connect()
            self.vc.play(discord.FFmpegPCMAudio(executable="C:/Users/T Bot/Downloads/ffmpeg-7.0-full_build/bin/ffmpeg.exe", source="hema.mp3"))

    def turntable(self, ctx):
        song = self.musicQueue.pop(0)
        self.vc.play(discord.FFmpegPCMAudio(executable="C:/Users/T Bot/Downloads/ffmpeg-7.0-full_build/bin/ffmpeg.exe", source=song), after=lambda e: self.nextSong(ctx))

    def nextSong(self, ctx):
        if self.musicQueue != []:
            self.playing = True
            self.turntable(ctx)
        else: 
            self.vc.disconnect()
            self.vc = None
            self.playing = False
    
    def getUrl(self, song):
        info = self.ytdl.extract_info(song, download=False)
        with open("info.json", 'w') as f:
            json.dump(info, f)
            f.flush()
            os.fsync(f.fileno())
        return info["entries"][0]["url"]

    @commands.command(name = "play", description = "Plays a song")
    async def play(self, ctx, *args):
        if self.vc == None or self.vc.channel != ctx.author.voice.channel:
            self.vc = await ctx.author.voice.channel.connect()
        argsString = " ".join(args)
        print(argsString)
        await ctx.send(content = "play " + argsString)
        self.musicQueue.append(self.getUrl(argsString))
        if not self.playing:
            self.turntable(ctx)

    