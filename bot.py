# bot.py
import discord
from discord import app_commands
from discord.ext import commands, tasks

import os
import asyncio
from dotenv import load_dotenv
import json
import datetime

import config
# import course_info
# import quotas_operations
# import subject_channels
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
TOKEN = os.getenv('DISCORD_TOKEN')

# Load admin's ID and test server ID
admin_id = int(os.getenv('ADMIN_ID'))
test_server_id = int(os.getenv('TEST_SERVER_ID'))

# Uncomment when running on replit (1/2)
# from keep_alive import keep_alive

# define bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="-", intents=intents, activity=discord.Game(name="Doki Doki Literature Club!"), help_command=None)

# Update quotas every 1.5 minutes
# quotas on the website is updated at 03, 18, 33, 48 minutes
@tasks.loop(seconds=90.0)
async def update_quotas():

    start_time = get_quota.update_time()
    print(f"Update started: {start_time}")
    update_time = await get_quota.download_quotas(bot, update_quotas.current_loop)
    print(f"Update finished: {update_time}: {update_quotas.current_loop}")

    # Send update confirmation message to quota-updates channel
    # Handle Discord API service issues
    try:
        update_channel = await bot.fetch_channel(1072569015089774622)
    except:
        return

    start_d = get_quota.disc_time(start_time, "d")  # Date in mm/dd/yyyy
    start_T = get_quota.disc_time(start_time, "T")  # Time (12h) in h:mm:ss
    update_d = get_quota.disc_time(update_time, "d")
    update_T = get_quota.disc_time(update_time, "T")

    try:
        await update_channel.send(f"🔃 Updated! {start_d} {start_T} - {update_d} {update_T}: {update_quotas.current_loop}")
    except:
        return

    # Confirm new subscribers and unsubscribe unreachable users
    await get_quota.check_on_everyone(bot)

    # # Start checking diffs after first loop run
    # if update_quotas.current_loop > 0:
    #     await get_quota.check_diffs()

# On ready event
# Display bot guilds
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild(s):\n'
            f'{guild.name}(id: {guild.id})'
        )
    # Prepare list of subject channels
    channels = await get_quota.get_channels(bot)
    print("Channels loaded!")

    await update_quotas.start()

@bot.event
async def on_guild_join(guild):
    await bot.tree.sync()
    print(
        f'{bot.user} joined the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

# Commands have been moved to Hill!

# Text commands start
# "sync" command
# Syncs command tree with Discord
@commands.guild_only()
@bot.command()
async def sync(ctx):
    if ctx.author.id == admin_id:  # Owner's ID
        # Sync global commands
        await bot.tree.sync()

        # Sync guild specific commands
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)

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