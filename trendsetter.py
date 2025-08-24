# change working directory to wherever trendsetter.py is in
import asyncio
import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import get_quota

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

load_dotenv()
TOKEN = os.getenv('TRENDSETTER_TOKEN')

# define bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="=", intents=intents, help_command=None)

# Update trends every 10 minutes
@tasks.loop(minutes=15.0)
async def set_trends():
    # Record start time of operation
    trend_start_time = get_quota.update_time()
    print(f"Trend update started: {trend_start_time}")

    # Run snapshot operation in executor because it takes very long
    loop = asyncio.get_running_loop()
    trend_snapshot_result = await loop.run_in_executor(None, get_quota.create_trend_snapshot)

    # Record end time of operation
    # Display error message if quotas file is corrupt
    trend_update_confirm_fail = "finished" if trend_snapshot_result else "failed"
    trend_update_end_time = get_quota.update_time()
    print(f"Trend update {trend_update_confirm_fail}: {trend_update_end_time}")

    # Send trend update confirmation/error message to quota-updates channel
    trend_start_d = get_quota.disc_time(trend_start_time, "d")  # Date in mm/dd/yyyy
    trend_start_T = get_quota.disc_time(trend_start_time, "T")  # Time (12h) in h:mm:ss
    trend_update_end_d = get_quota.disc_time(trend_update_end_time, "d")
    trend_update_end_T = get_quota.disc_time(trend_update_end_time, "T")

    # Send update confirmation message to quota-updates channel
    # Handle Discord API service issues
    try:
        update_channel = await bot.fetch_channel(1072569015089774622)
        await update_channel.send(f"📈 Trend update {trend_update_confirm_fail}! {trend_start_d} {trend_start_T} - {trend_update_end_d} {trend_update_end_T}")
    except:
        return
    
# On ready event
# Display bot guilds
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild(s):\n'
            f'{guild.name}(id: {guild.id})'
        )

    await set_trends.start()

# Launch bot
bot.run(TOKEN)