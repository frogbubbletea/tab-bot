# hill.py
import discord
from discord import app_commands
from discord.ext import commands

import os
from dotenv import load_dotenv

import get_quota

# Uncomment when running on Windows
# Fixes runtime error: asyncio.run() cannot be called from a running event loop
#import nest_asyncio
#nest_asyncio.apply()

# change working directory to wherever bot.py is in
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# load bot token
load_dotenv()
TOKEN = os.getenv('HILL_TOKEN')

# Uncomment when running on replit (1/2)
# from keep_alive import keep_alive

# define bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=",", intents=intents, activity=discord.Game(name="Doki Doki Literature Club!"), help_command=None)

# On ready event
# Display bot guilds
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild(s):\n'
            f'{guild.name}(id: {guild.id})'
        )

# Sync slash command tree with new guild
@bot.event
async def on_guild_join(guild):
    await bot.tree.sync()
    print(
        f'{bot.user} joined the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

# Slash commands start
# "quota" command
# Lists quotas of all sections of a course
@bot.tree.command(description="Get quotas for a course!", guilds=bot.guilds)
async def quota(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    embed_quota = get_quota.compose_message(course_code.replace(" ", "").upper())
    
    if embed_quota == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            await interaction.edit_original_response(embed=embed_quota)
        except:
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")

# "info" command
# Shows course info
@bot.tree.command(description="Get the information of a course!", guilds=bot.guilds)
async def info(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    embed_info = get_quota.compose_info(course_code.replace(" ", "").upper())

    if embed_info == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            await interaction.edit_original_response(embed=embed_info)
        except:
            await interaction.edit_original_response(content="⚠️ Course info too long!\nDue to a Discord limitation, course info is limited to 1024 characters long.")

# "sections" command
# Lists sections of a course and their times, venues and instructors
@bot.tree.command(description="Get sections of a course!", guilds=bot.guilds)
async def sections(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    embed_sections = get_quota.compose_sections(course_code.replace(" ", "").upper())

    if embed_sections == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            await interaction.edit_original_response(embed=embed_sections)
        except:
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, courses with more than 25 sections cannot be displayed.")
# Slash commands end

# Text commands start
# "sync" command
# Syncs command tree with Discord
@bot.command()
async def sync(ctx):
    if ctx.author.id == 740098404688068641:
        await bot.tree.sync()
        await ctx.send("👍 Commands synced!")
    else:
        await ctx.send("🚫 This command can only be ran by the admin!")
# Text commands end

# Uncomment when running on replit (2/2)
# keep_alive()

# (text) command not found error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.CommandNotFound):
        return
    raise error

# Launch bot
bot.run(TOKEN)