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
import course_info
import quotas_operations
import subject_channels

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

# Uncomment when running on replit (1/2)
# from keep_alive import keep_alive

# define bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents=intents, activity=discord.Game(name="Taiko no Tatsujin"), help_command=None)

# Dict containing all subject channels
channels = None

# Helper function to check if course/section/quota changed
async def check_diffs():
    # Open quotas files
    new_quotas = quotas_operations.open_quotas()
    old_quotas = open('quotas_old.json', encoding='utf-8')
    try:
        old_quotas = json.load(old_quotas)
    except:
        return

    # No comparison if current quotas file or last quotas file is corrupted
    if (not quotas_operations.check_quotas_validity) or (old_quotas == {}):
        return
    
    for key, value in new_quotas.items():
        # Skip 'time' entry
        if key == 'time':
            continue
        # New course
        if key not in old_quotas:
            await channels.get(key[0: 4], channels['other']).send(f"🥑 New course!\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
        else:
            for key2, value2 in value['sections'].items():
                # New section
                if key2 not in old_quotas[key]['sections']:
                    quota_new = value2[4].split("\n", 1)[0]
                    await channels.get(key[0: 4], channels['other']).send(f"🍅 New section!\n{value.get('title', 'Error')}: {key2}\nQuota: {quota_new}")
                # Quota change
                elif value2[4] != old_quotas[key]['sections'][key2][4]:  # DEBUG: Compare waitlist instead of quota 
                    quota_old = old_quotas[key]['sections'][key2][4].split("\n", 1)[0]
                    quota_new = value2[4].split("\n", 1)[0]
                    await channels.get(key[0: 4], channels['other']).send(f"🍋 Quota changed!\n{value.get('title', 'Error')}: {key2}\n{quota_old} -> {quota_new}")

# Update quotas every 15 minutes, at roughly the same time quotas on the website is updated (03, 18, 33, 48)
@tasks.loop(seconds=900.0)
async def update_quotas():

    start_time = course_info.update_time()
    print(f"Update started: {start_time}")
    update_time = course_info.download_quotas()
    print(f"Update finished: {update_time}: {update_quotas.current_loop}")

    # Send update confirmation message to quota-updates channel
    update_channel = await bot.fetch_channel(1072569015089774622)
    await update_channel.send(f"🔃 Updated! {start_time} - {update_time}: {update_quotas.current_loop}")

    # Start checking diffs after first loop run
    if update_quotas.current_loop > 0:
        await check_diffs()

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
    global channels
    channels = await subject_channels.find_channels(bot)
    print("Channels loaded!")

    await update_quotas.start()

@bot.event
async def on_guild_join(guild):
    await bot.tree.sync()
    print(
        f'{bot.user} joined the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

# Slash commands start
# "test" command
# Tests bot status
@bot.tree.command(description="Tests bot status", guilds=bot.guilds)
async def test(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("meow")

@bot.tree.command(description="Get quota information for a course!", guilds=bot.guilds)
async def quota(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    embed_quota = quotas_operations.compose_message(course_code.replace(" ", "").upper())
    
    if embed_quota == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            await interaction.edit_original_response(embed=embed_quota)
        except:
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")
# Slash commands end

# Text commands start
# "sync" command
# Syncs command tree with Discord
@commands.guild_only()
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