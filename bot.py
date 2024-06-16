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
from pytz import timezone
from dotenv import load_dotenv, set_key
from datetime import timedelta
from discord.ui import Button, View
from async_timeout import timeout
from discord.ext import commands
from discord.ext import tasks

from music_cog import music_cog

# Silence useless bug reports messages
yt_dlp.utils.bug_reports_message = lambda: ""

global dotenvFile
dotenvFile = "API.env"
load_dotenv(dotenvFile)

#plimpoes
# token = os.getenv("PLIMPOES")

#testbot
token = os.getenv('TESTBOT')

canvastoken = os.getenv('CANVAS')

print(token)
print(canvastoken)
# Testing fakedata
# assUrlList = ['wowwieee its a link']

# Actual data
assUrlList = [
    'https://canvas.utwente.nl/api/v1/courses/14218/assignments?access_token=',
    'https://canvas.utwente.nl/api/v1/courses/14555/assignments?access_token='
]
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

assignment_json = "data.json"

with open('data.json', 'r') as f:
    assData = json.load(f)

def updateData():
    with open('data.json', 'w') as f:
        json.dump(assData, f)
        f.flush()
        os.fsync(f.fileno())

with open('quote.json', 'r') as f:
    quoteData = json.load(f)

def updateQuote():
    with open('quote.json', 'w') as f:
        json.dump(quoteData, f)
        f.flush()
        os.fsync(f.fileno())

plimpoesEmbed = discord.Embed(title="plimpoes", colour=0x7F684F)
plimpoesEmbed.set_image(
    url="https://media.discordapp.net/stickers/1062405909910933565.webp?size=160"
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot("", description="plimpoes", intents=intents)


@bot.event
async def on_ready():
    global guild
    global role

    # Actual server
    # guild = bot.get_guild(1175750255808094220)

    # Test server
    guild = bot.get_guild(1072906075373834250)

    
    # await bot.add_cog(Music(bot))
    await bot.add_cog(music_cog(bot))
    try:
        synced = await bot.tree.sync()
        print("succeed " + str(len(synced)))
    except Exception as e:
        print("failed " + str(e))
    assignmentcheck.start()
    print(f"Logged on as {bot.user}! (ID: {bot.user.id})")
    role = discord.utils.get(guild.roles, name="assignments ping")


@tasks.loop(seconds=60)
async def assignmentcheck():
    global role
    global weekMessage
    global assUrlList
    global assData  

    print("Checking assignments")

    currentday = datetime.datetime.now() + timedelta(hours=1)
    timezonedate = datetime.datetime.now().astimezone(timezone("Europe/Amsterdam")).replace(tzinfo=None)
    utctime = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    hoursdelta = math.ceil((timezonedate - utctime).total_seconds()) // 3600
    print("UTC time: " + str(utctime))
    print("Hours delta: " + str(hoursdelta))
    print("Europe time: " + str(timezonedate))
    print("Huidige tijd:" + str(currentday))
    for url in assUrlList:

        response = urllib.request.urlopen(url + canvastoken)
        data = response.read().decode("utf-8", "ignore")
        data = json.loads(data)

        courseresponse = urllib.request.urlopen(' https://canvas.utwente.nl/api/v1/courses' + '?access_token=' + canvastoken)
        coursedata = courseresponse.read().decode("utf-8", "ignore")
        coursedata = json.loads(coursedata)

        edited = False

        for i in data:
            due = i["due_at"]
            assname = i["name"]
            hurl = i["html_url"]
            id = i["id"]
            print(id)
            if due is not None:
                date, time = due.split("T")
                time = time[:-1]
                date = date.split("-")
                time = time.split(":")
                assignmentdaytime = datetime.datetime(
                    int(date[0]),
                    int(date[1]),
                    int(date[2]),
                    (int(time[0]) + hoursdelta) % 24,
                    int(time[1]),
                    int(time[2]),
                )

                for course in coursedata:
                    if course["id"] == i["course_id"]:
                        courseName = course["name"]
                        break

                try:
                    for channel in assData["data"]:
                        chan = bot.get_channel(int(channel))
                        if timezonedate <= assignmentdaytime:
                            print("hasnt passed yet")
                            if str(id) not in assData["data"][channel]: # The assignment is new and is to be added
                                print(due)
                                await assignmentSend(chan, assname, assignmentdaytime, hurl, 0, courseName)
                                
                            elif ("24hour" not in assData["data"][channel][str(id)] and (assignmentdaytime - timezonedate).days == 0
                            and "1hour" not in assData["data"][channel][str(id)]): # Assignment is due in 24 hours
                                print("Assignment due in 24 hours")
                                await assignmentSend(chan, assname, assignmentdaytime, hurl, 1, courseName)

                            elif ("1hour" not in assData["data"][channel][str(id)]
                            and (assignmentdaytime - timezonedate).days == 0
                            and (assignmentdaytime - timezonedate).seconds < 3600): # Assignment is due in 1 hour
                                print("Assignment due in 1 hour")
                                await assignmentSend(chan, assname, assignmentdaytime, hurl, 2, courseName)

                        elif str(id) in assData["data"][channel]: # Assignment is overdue but still in the list huh?
                            print("Assignment overdue")
                            try:
                                for timeslot, message in assData["data"][channel][str(id)].items():
                                    message = await chan.fetch_message(message)
                                    await message.delete()
                            except:
                                print("An error occurred while deleting the message")
                            print(assData["data"][channel][str(id)])
                            assData["data"][channel].pop(str(id))
                            edited = True

                    if edited:
                        print("Saving the data")
                        updateData()

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

    print(assignmentdaytime)

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

            musicEmbed = discord.Embed(
                title = ":dvd: Currently inactive :dvd:",
                url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                colour = 0x7F684F
            )
            musicEmbed.set_thumbnail(url="https://i.ytimg.com/vi/gG_dA32oH44/maxresdefault.jpg")
            musicEmbed.add_field(name="Artist", value = "Rick Astley")
            musicEmbed.add_field(name="Length", value = "3:33")
            musicEmbed.add_field(name="Queue Length", value = "5")

            await chan.send(embed=musicEmbed)

            return
        elif "this assignment channel" in message.content:
            if str(message.channel.id) not in assData["data"]:
                assData["data"][message.channel.id] = {}
                chan = bot.get_channel(message.channel.id)
                await chan.purge()
                await chan.send(embed=plimpoesEmbed)
                #TODO add the sending of the messages
            else:
                chan = bot.get_channel(message.channel.id)
                print("purging")
                await chan.purge()
                return
            
            updateData()

        elif "quoteSetup" in message.content:
            if str(message.guild.id) not in quoteData:
                quoteData[str(message.guild.id)] = {}
                quoteData[str(message.guild.id)]['channel'] = message.channel.id
                quoteData[str(message.guild.id)]['quotes'] = {}
                quoteData[str(message.guild.id)]['emoji'] = message.content.split(" ")[1]
                updateQuote()
                await message.channel.purge()
                await message.channel.send(embed=plimpoesEmbed)
            else:
                await message.channel.send("A quote channel has already been selected")
            print(quoteData)
        else:
            message.content = "MUSIC " + message.content
            await bot.process_commands(message)
        
        if str(message.channel) == "plimpoes-appreciation-channel":
            await message.channel.send(embed=plimpoesEmbed)
    elif (message.author == bot.user and str(message.channel.id) in assData["data"]):
        print(message.embeds[0].fields[0].value)
        match message.embeds[0].title:
            case "New assignment created!" | "Current assignment!":
                assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]] = {}
                assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]]["initial"] = message.id
                print("New assignment created")
            case "Assignment due in 24 hours!":
                assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]]["24hour"] = message.id
                delete_message = await message.channel.fetch_message(assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]]["initial"])
                await delete_message.delete()
                assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]].pop("initial")
                print("24 hours left")
            case "Assignment due in 1 hour!":
                assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]]["1hour"] = message.id
                delete_message = await message.channel.fetch_message(assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]]["24hour"])
                await delete_message.delete()
                assData["data"][str(message.channel.id)][message.embeds[0].url.split("/")[-1]].pop("24hour")
                print("1 hour left")
        print("New bot message: " + str(message.embeds))

        updateData()

    return First

# On reaction add, if it is the selected quote emoji, quote the message in the quote channel
@bot.event
async def on_raw_reaction_add(reaction):
    message = await bot.get_channel(reaction.channel_id).fetch_message(reaction.message_id)
    if (message.author != bot.user 
        and str(reaction.emoji) == quoteData[str(reaction.guild_id)]["emoji"] 
        and message.channel.permissions_for(message.guild.default_role).send_messages == True 
        and (str(message.id) not in quoteData[str(reaction.guild_id)]["quotes"])):
            quoter = await bot.fetch_user(reaction.user_id)
            quoteData[str(reaction.guild_id)]["quotes"][str(message.id)] = str((
                await bot.get_channel(quoteData[str(reaction.guild_id)]["channel"]).send(embed=await embedQuote(message.content, message.author, quoter), allowed_mentions=discord.AllowedMentions(roles=False, users=False, everyone=False))
                ).id)
            updateQuote()

# On reaction remove, if it is the selected quote emoji, delete the quote in the quote channel if none left afterwards
@bot.event
async def on_raw_reaction_remove(reaction):
    quote_emoji = quoteData[str(reaction.guild_id)]["emoji"]
    message = await bot.get_channel(reaction.channel_id).fetch_message(reaction.message_id)
    if message.author != bot.user and str(reaction.emoji == quote_emoji) and message.channel.permissions_for(message.guild.default_role).send_messages == True:
        print(message.reactions)
        if not (any(map(lambda reaction: reaction.emoji == quote_emoji, message.reactions))):
            deleteMessage = await bot.get_channel(quoteData[str(reaction.guild_id)]["channel"]).fetch_message(quoteData[str(reaction.guild_id)]["quotes"][str(message.id)])
            await deleteMessage.delete()
            quoteData[str(reaction.guild_id)]["quotes"].pop(str(message.id))
            updateQuote()

# Generate an embed with a quote and all the neccesary information
async def embedQuote(quote, person, quoter):
    print(type(person))
    if isinstance(person, discord.User):
        quoteEmbed = discord.Embed(
            description="<@" + str(person.id) + ">",
            colour = 0x7F684F,
            timestamp=datetime.datetime.now()
        )
        quoteEmbed.set_thumbnail(url=person.avatar.url)

    else:
        quoteEmbed = discord.Embed(
            description=str(person),
            colour = 0x7F684F,
            timestamp=datetime.datetime.now()
        )
        try:
            print(int(person[2:-1]))
            user = await bot.fetch_user(int(person[2:-1]))
            print("WTF???")
            print(type(user))
            print(user)
            print(user.display_avatar.url)
            quoteEmbed.set_thumbnail(url=user.display_avatar.url)
        except:
            print("No thumbnail found")

    quoteEmbed.add_field(name=str(quote) + "\n", value="Originally quoted by: <@" + str(quoter.id) + ">", inline=True)
    quoteEmbed.set_footer(text="-", icon_url=quoter.avatar.url)
    print(type(person))
    return quoteEmbed

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

# Quote a message in the quote channel
@bot.tree.command(
    name="quote", description="Insert a new quote"
)
async def quote(interaction: discord.Interaction, person: str, quote: str):
    if (quoteData[str(interaction.guild_id)] != None):
        message = await bot.get_channel(quoteData[str(interaction.guild_id)]["channel"]).send(embed=await embedQuote(quote, person, interaction.user), allowed_mentions=discord.AllowedMentions(roles=False, users=False, everyone=False))
        quoteData[str(interaction.guild_id)]["quotes"][str(message.id)] = str(message.id)
        await interaction.response.send_message(content="Succesfully send to quote channel", ephemeral=True, delete_after=5)
    else:
        await interaction.response.send_message("A quote channel has not been selected yet", ephemeral=True, delete_after=5)

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

@bot.tree.command(name="assignment-setup", description="Sets up the assignment channel")
async def setupAssignments(interaction: discord.Interaction):
    guild = interaction.guild_id
    channel = interaction.channel_id
    assData[str(guild)] = {}
    assData[str(guild)]["channel"] = channel
    assData[str(guild)]["courses"] = {}

    updateData()

    channel = bot.get_channel(channel)

    await interaction.response.send_message("Succesfully set up the assignment channel", ephemeral=True, delete_after=5)

    await channel.purge()
    await channel.send(embed=plimpoesEmbed)

@bot.tree.command(name="add-key", description="Adds a new API key to your profile ~~securly~~")
async def addAPIKey(interaction: discord.Interaction):
    # TODO
    interaction.response.send_message("Removed the assignment channel", ephemeral=True, delete_after=5)

# Command for adding a new course for reminders
@bot.tree.command(name="assignment-add", description="Adds a new course")
async def addCourse(interaction: discord.Interaction, courseid: str, apikey: str, enddate: str):
    guild = interaction.guild
    guildid = guild.id
    userID = str(interaction.user.id)

    try:
        endDate_datetime = datetime.datetime.strptime(enddate, "%Y-%m-%d")
    except ValueError:
        await interaction.response.send_message("Invalid date format, please use YYYY-MM-DD", ephemeral=True, delete_after=5)

    getEnv = os.getenv(userID)
    if getEnv == None:
        set_key(dotenvFile, userID, apikey)
        load_dotenv(dotenvFile)
    else:
        apikey = os.getenv(userID)

    try:
        data = getCanvasData(courseid, apikey, True)
    except:
        await interaction.response.send_message("Invalid course ID or API key", ephemeral=True, delete_after=5)
        return

    newChannel = await createAssChannel(guild, data["name"], interaction.user)

    assData[str(guildid)]["courses"][courseid] = {"name": data["name"], "channel": newChannel, "API": userID, "participants": [userID], "enddate": enddate, "assignments": {}}
    updateData()

    await interaction.response.send_message("Succesfully added the course", ephemeral=True, delete_after=5)

    joinMessage = await bot.get_channel(int(assData[str(guildid)]["channel"])).send(embed=assignmentEmbed(data["name"], endDate_datetime, interaction.user, courseid), view=assignmentView())
    assData[str(guildid)]["courses"][courseid]["joinMessage"] = joinMessage.id

# Create an embed for a newly added course with assignments
def assignmentEmbed(course, endDate, user, courseID):
    assignmentEmbed = discord.Embed(
        title=course,
        colour=0x7F684F,
        timestamp=endDate,
        url="https://canvas.utwente.nl/courses/" + courseID,
    )
    assignmentEmbed.set_author(name="New course has been added!")
    assignmentEmbed.set_footer(icon_url=user.display_avatar.url, text=f"Added by {user.name}  | Course ID: {courseID}")

    return assignmentEmbed

# Create the view with buttons for a new assignment message.
def assignmentView():
    view = View()
    join = Button(label = "Join reminders", style = discord.ButtonStyle.primary)
    join.callback = joinReminders
    leave = Button(label = "Leave reminders", style = discord.ButtonStyle.danger)
    leave.callback = leaveReminders
    view.add_item(join)
    view.add_item(leave)
    return view

# Button callback for joining a course
async def joinReminders(interaction: discord.Interaction):
    guild = interaction.guild_id
    userID = str(interaction.user.id)
    courseID = interaction.message.embeds[0].footer.text.split("Course ID: ")[1]
    assData[str(guild)]["courses"][courseID]["participants"].append(userID)
    updateData()
    await interaction.response.send_message("Succesfully joined the reminders", ephemeral=True, delete_after=5)

    await bot.get_channel(int(assData[str(str(guild))]["courses"][courseID]["channel"])).set_permissions(interaction.user, view_channel=True)

# Button callback for leaving a course
async def leaveReminders(interaction: discord.Interaction):
    guild = interaction.guild_id
    userID = str(interaction.user.id)
    courseID = interaction.message.embeds[0].footer.text.split("Course ID: ")[1]
    try:
        assData[str(guild)]["courses"][courseID]["participants"].remove(userID)
        updateData()
        await interaction.response.send_message("Succesfully left the reminders", ephemeral=True, delete_after=5)

        await bot.get_channel(int(assData[str(str(guild))]["courses"][courseID]["channel"])).set_permissions(interaction.user, view_channel=False)
    except:
        await interaction.response.send_message("You are not in the list of participants", ephemeral=True, delete_after=5)

# Method for getting the data from the Canvas API for a course or all assignments of a course
def getCanvasData(course, APIKey, isCourse):
    base = 'https://canvas.utwente.nl/api/v1/courses/' + str(course)
    request = base if isCourse else base + '/assignments'

    response = urllib.request.urlopen(request + '?access_token=' + APIKey)
    data = response.read().decode("utf-8", "ignore")
    data = json.loads(data)

    return data

# Method for creating a new assignment channel
async def createAssChannel(guild, name, user):
    category = discord.utils.get(guild.categories, name="Assignments")
    if category == None:
        category = await guild.create_category_channel("Assignments")
    channel = discord.utils.get(category.text_channels, name=name)
    if channel == None:
        channel = await category.create_text_channel(name)
        await channel.set_permissions(user, view_channel=True)
        await channel.set_permissions(guild.default_role, view_channel=False, send_messages=False)

    return channel.id

bot.run(token)
