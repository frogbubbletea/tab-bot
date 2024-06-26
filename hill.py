# hill.py
# Start bot.py before starting this to ensure Hill is reading the same database as Tab!
import discord
from discord import app_commands
from discord.ext import commands

from tinydb import TinyDB, Query

import os
from dotenv import load_dotenv
import typing
import re
from datetime import datetime

import get_quota
import plot_quota  # v3.0 features are hidden until hardware incompatibility is resolved! 1/3
import config

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

# Load admin's ID and test server ID
admin_id = int(os.getenv('ADMIN_ID'))
test_server_id = int(os.getenv('TEST_SERVER_ID'))

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
# Compose page flip buttons for all commands
class QuotaPage(discord.ui.View):
    def __init__(self, *, timeout=180, mode="q", course_code="", page=0, semester="", room=""):
        super().__init__(timeout=timeout)
        self.mode = mode
        self.course_code = course_code
        self.page = page
        self.semester = semester
        self.room = room

    @discord.ui.button(label="Previous page", style=discord.ButtonStyle.gray, emoji="⬅️")
    async def previous_button(self,interaction:discord.Interaction, button:discord.ui.Button):
        if self.mode == "q":
            embed_quota_pageflip = get_quota.compose_message(self.course_code, self.page - 1, self.semester)
        elif self.mode == "s":
            embed_quota_pageflip = get_quota.compose_sections(self.course_code, self.page - 1, self.semester)
        elif self.mode == "i":
            embed_quota_pageflip = get_quota.compose_info(self.course_code, self.page - 1, self.semester)
        elif self.mode == "l":
            embed_quota_pageflip = get_quota.compose_list(self.course_code, self.page - 1, self.semester)
        elif self.mode == "a":
            embed_quota_pageflip = get_quota.compose_about(len(bot.guilds), self.page - 1)
        elif self.mode == "r":
            embed_quota_pageflip = get_quota.compose_room_schedule(self.room, self.page - 1)
        
        if embed_quota_pageflip == "p0":
            await interaction.response.send_message("🚫 You're already at the first page!", ephemeral=True)
        else:
            try:
                await interaction.response.edit_message(embed=embed_quota_pageflip, view=self)
            except:  # Highly unlikely to happen
                await interaction.response.send_message(f"⚠️ Error: {embed_quota_pageflip}!")
            else:
                self.page -= 1

    @discord.ui.button(label="Next page", style=discord.ButtonStyle.gray, emoji="➡️")
    async def next_button(self,interaction:discord.Interaction, button:discord.ui.Button):
        if self.mode == "q":
            embed_quota_pageflip = get_quota.compose_message(self.course_code, self.page + 1, self.semester)
        elif self.mode == "s":
            embed_quota_pageflip = get_quota.compose_sections(self.course_code, self.page + 1, self.semester)
        elif self.mode == "i":
            embed_quota_pageflip = get_quota.compose_info(self.course_code, self.page + 1, self.semester)
        elif self.mode == "l":
            embed_quota_pageflip = get_quota.compose_list(self.course_code, self.page + 1, self.semester)
        elif self.mode == "a":
            embed_quota_pageflip = get_quota.compose_about(len(bot.guilds), self.page + 1)
        elif self.mode == "r":
            embed_quota_pageflip = get_quota.compose_room_schedule(self.room, self.page + 1)

        if embed_quota_pageflip == "pmax":
            await interaction.response.send_message("🚫 You're already at the last page!", ephemeral=True)
        else:
            try:
                await interaction.response.edit_message(embed=embed_quota_pageflip, view=self)
            except:  # Highly unlikely to happen
                await interaction.response.send_message(f"⚠️ Error: {embed_quota_pageflip}!")
            else:
                self.page += 1

# "quota" command
# Lists quotas of all sections of a course
@bot.tree.command(description="Get quotas of a course!")
@app_commands.describe(course_code="Course code")
@app_commands.describe(semester_name="The semester to look up in. Leave empty for current semester!")
async def quota(interaction: discord.Interaction, course_code: str, semester_name: typing.Optional[str]):
    await interaction.response.defer(thinking=True)
    course_code = course_code.replace(" ", "").upper()

    semester = get_quota.semester_string_to_code(semester_name)
    if not semester_name:  # if semester is empty then check current semester
        semester = ""
    elif semester == -1:  # Error: invalid semester
        await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
        return

    embed_quota = get_quota.compose_message(course_code, semester=semester)
    
    # Error: Course data unavailable
    if embed_quota == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_quota == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    # Error: Course has no sections (unlikely)
    elif embed_quota == "no_sections":
        await interaction.edit_original_response(content="⚠️ This course has no sections!")
    else:
        try:
            view = QuotaPage(mode="q", course_code=course_code, semester=semester)
            # Add source button linking to course entry in original course quota website
            if not semester:  # Do not add source button for previous semesters
                get_quota.add_source_url(view, course_code)
            await interaction.edit_original_response(embed=embed_quota, view=view)
        except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")

# "info" command
# Shows course info
@bot.tree.command(description="Get the information about a course!")
@app_commands.describe(course_code="Course code")
@app_commands.describe(semester_name="The semester to look up in. Leave empty for current semester!")
async def info(interaction: discord.Interaction, course_code: str, semester_name: typing.Optional[str]) -> None:
    await interaction.response.defer(thinking=True)
    course_code = course_code.replace(" ", "").upper()

    semester = get_quota.semester_string_to_code(semester_name)
    if not semester_name:  # if semester is empty then check current semester
        semester = ""
    if semester == -1:  # Error: invalid semester
        await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
        return

    embed_info = get_quota.compose_info(course_code, semester=semester)

    # Error: Course data unavailable
    if embed_info == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_info == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            view = QuotaPage(mode="i", course_code=course_code, semester=semester)
            # Clear page buttons if no course requires/excludes it
            if not (get_quota.get_required_by_courses(course_code, "p") + get_quota.get_required_by_courses(course_code, "e")):
                view.clear_items()
            # Add source and reviews button
            if not semester:  # Do not add source button for previous semesters
                get_quota.add_source_url(view, course_code)
            get_quota.add_space_url(view, course_code)

            await interaction.edit_original_response(embed=embed_info, view=view)
        except:  # Deprecated: long course info text should be displayed correctly by splitting into multiple fields
            await interaction.edit_original_response(content="⚠️ Course info too long!\nDue to a Discord limitation, course info is limited to 1024 characters long.")

# "sections" command
# Lists sections of a course and their times, venues and instructors
@bot.tree.command(description="Get sections of a course!")
@app_commands.describe(course_code="Course code")
@app_commands.describe(semester_name="The semester to look up in. Leave empty for current semester!")
async def sections(interaction: discord.Interaction, course_code: str, semester_name: typing.Optional[str]) -> None:
    await interaction.response.defer(thinking=True)
    course_code = course_code.replace(" ", "").upper()

    semester = get_quota.semester_string_to_code(semester_name)
    if not semester_name:  # if semester is empty then check current semester
        semester = ""
    if semester == -1:  # Error: invalid semester
        await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
        return

    embed_sections = get_quota.compose_sections(course_code, semester=semester)

    # Error: Course data unavailable
    if embed_sections == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_sections == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    # Error: Course has no sections (unlikely)
    elif embed_sections == "no_sections":
        await interaction.edit_original_response(content="⚠️ This course has no sections!")
    else:
        try:
            view = QuotaPage(mode="s", course_code=course_code, semester=semester)
            # Add source button linking to course entry in original course quota website
            if not semester:
                get_quota.add_source_url(view, course_code)
            await interaction.edit_original_response(embed=embed_sections, view=view)
        except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, courses with more than 25 sections cannot be displayed.")

# "list" command
# List all courses with given query
@bot.tree.command(description="Search courses by prefix/instructor/common core area!")
@app_commands.describe(query="Course code prefix/instructor/common core area")
@app_commands.describe(semester_name="The semester to look up in. Leave empty for current semester!")
async def search(interaction: discord.Interaction, query: str, semester_name: typing.Optional[str]) -> None:
    await interaction.response.defer(thinking=True)

    semester = get_quota.semester_string_to_code(semester_name)
    if not semester_name:  # if semester is empty then check current semester
        semester = ""
    if semester == -1:  # Error: invalid semester
        await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
        return

    cc_areas = get_quota.get_cc_areas(semester)
    instructors = get_quota.get_attribute_list(3, semester) + get_quota.get_attribute_list(4, semester)

    # Submit query to search function
    embed_list = get_quota.compose_list(query, semester=semester)

    # Error: Course data unavailable
    if embed_list == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: invalid query
    elif embed_list == "key":
        await interaction.edit_original_response(content="⚠️ No courses found!")
    else:
        view = QuotaPage(mode="l", course_code=query, semester=semester)
        # Add source button linking to course entry in original course quota website
        # Only add source URL for prefix and instructor searches
        if not semester:
            if query in instructors:
                get_quota.add_source_url(view, query, "i")
            elif query not in cc_areas + instructors:
                get_quota.add_source_url(view, query, "l")
        await interaction.edit_original_response(embed=embed_list, view=view)

# "graph" command (hidden until hardware incompatibility resolved! 2/3)
# Plot the enrollment statistics of a section over time
@bot.tree.command(description="Plot the enrollment statistics of a section over time!")
@app_commands.describe(course_code="Course code")
@app_commands.describe(section="Name of the section")
@app_commands.describe(semester="The semester to look up in. Leave empty for current semester!")
async def graph(interaction: discord.Interaction, course_code: str, section: str, semester: typing.Optional[str]) -> None:
    await interaction.response.defer(thinking=True)

    # Check for specified semester
    sem = plot_quota.semester_string_to_code_trend(semester)
    if not semester:  # Use current semester if not specified
        sem = ""
    elif sem == -1:  # Error: Invalid semester
        await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
        return

    course_code = course_code.replace(" ", "").upper()
    section = section.replace(" ", "").upper()
    embed_plot, section_plot_image_file = plot_quota.compose_embed_with_plot(course_code, section, sem=sem)

    # Error: Course data unavailable
    if embed_plot == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: invalid course code
    elif embed_plot == "course_code":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    # Error: invalid section code
    elif embed_plot == "section_code":
        await interaction.edit_original_response(content="⚠️ Check your section code!")
    else:
        view = QuotaPage(mode="p", course_code=course_code)
        view.clear_items()
        # Add source button, do not add for past semesters
        if not sem:
            get_quota.add_source_url(view, course_code)
        await interaction.edit_original_response(embed=embed_plot, view=view, attachments=[section_plot_image_file])

# "room" command group start
room_group = app_commands.Group(name="room", description="Get the schedule of a room!")

# "room schedule" command
# Shows the status of a room right now and its schedule this week
@room_group.command(name="schedule", description="Get the class schedule of a room right now and this week!")
@app_commands.describe(room="Room number")
async def room_schedule(interaction: discord.Interaction, room: str) -> None:
    await interaction.response.defer(thinking=True)

    embed_room_schedule = get_quota.compose_room_schedule(room)

    # Error: Course data unavailable
    if embed_room_schedule == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: invalid room code
    elif embed_room_schedule == "key":
        await interaction.edit_original_response(content="⚠️ Check your room code!")
    else:
        view = QuotaPage(mode="r", room=room)
        await interaction.edit_original_response(embed=embed_room_schedule, view=view)

# "room" command group end
bot.tree.add_command(room_group)

# "history" command group start
# history_group = app_commands.Group(name="history", description="Get course data from a previous semester!")

# "history quota" command
# Shows quotas of a course in a previous semester
# @history_group.command(name="quota", description="Get quotas of a course in a previous semester!")
# async def history_quota(interaction: discord.Interaction, course_code: str, semester_string: str) -> None:
#     await interaction.response.defer(thinking=True)
#     course_code = course_code.replace(" ", "").upper()

#     semester = get_quota.semester_string_to_code(semester_string)
#     if semester == -1:  # Error: invalid semester
#         await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
#         return

#     embed_quota = get_quota.compose_message(course_code, semester=semester)

#     # Error: Course data unavailable
#     if embed_quota == "unavailable":
#         await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
#     # Error: Invalid course code
#     elif embed_quota == "key":
#         await interaction.edit_original_response(content="⚠️ Check your course code!")
#     # Error: Course has no sections (unlikely)
#     elif embed_quota == "no_sections":
#         await interaction.edit_original_response(content="⚠️ This course has no sections!")
#     else:
#         try:
#             view = QuotaPage(mode="q", course_code=course_code, semester=semester)
#             await interaction.edit_original_response(embed=embed_quota, view=view)
#         except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
#             await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")

# "history sections" command
# Shows sections of a course and their schedules in a previous semester
# @history_group.command(name="sections", description="Get sections of a course in a previous semester!")
# async def history_sections(interaction: discord.Interaction, course_code: str, semester_string: str) -> None:
#     await interaction.response.defer(thinking=True)
#     course_code = course_code.replace(" ", "").upper()

#     semester = get_quota.semester_string_to_code(semester_string)
#     if semester == -1:  # Error: invalid semester
#         await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
#         return
    
#     embed_sections = get_quota.compose_sections(course_code, semester=semester)

#     # Error: Course data unavailable
#     if embed_sections == "unavailable":
#         await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
#     # Error: Invalid course code
#     elif embed_sections == "key":
#         await interaction.edit_original_response(content="⚠️ Check your course code!")
#     # Error: Course has no sections (unlikely)
#     elif embed_sections == "no_sections":
#         await interaction.edit_original_response(content="⚠️ This course has no sections!")
#     else:
#         try:
#             view = QuotaPage(mode="s", course_code=course_code, semester=semester)
#             await interaction.edit_original_response(embed=embed_sections, view=view)
#         except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
#             await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, courses with more than 25 sections cannot be displayed.")

# "history info" command
# Shows course info in a previous semester
# @history_group.command(name="info", description="Get the information about a course in a previous semester!")
# async def history_info(interaction: discord.Interaction, course_code: str, semester_string: str) -> None:
#     await interaction.response.defer(thinking=True)
#     course_code = course_code.replace(" ", "").upper()

#     semester = get_quota.semester_string_to_code(semester_string)
#     if semester == -1:  # Error: invalid semester
#         await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
#         return
    
#     embed_info = get_quota.compose_info(course_code, semester=semester)

#     # Error: Course data unavailable
#     if embed_info == "unavailable":
#         await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
#     # Error: Invalid course code
#     elif embed_info == "key":
#         await interaction.edit_original_response(content="⚠️ Check your course code!")
#     # Error: Course has no sections (unlikely)
#     elif embed_info == "no_sections":
#         await interaction.edit_original_response(content="⚠️ This course has no sections!")
#     else:
#         try:
#             view = QuotaPage(mode="i", course_code=course_code, semester=semester)
#             # Clear page buttons if no course requires/excludes it
#             if not (get_quota.get_required_by_courses(course_code, "p") + get_quota.get_required_by_courses(course_code, "e")):
#                 view.clear_items()
#             # Add reviews button
#             get_quota.add_space_url(view, course_code)

#             await interaction.edit_original_response(embed=embed_info, view=view)
#         except:  # Deprecated: long course info text should be displayed correctly by splitting into multiple fields
#             await interaction.edit_original_response(content="⚠️ Course info too long!\nDue to a Discord limitation, course info is limited to 1024 characters long.")

# "history search" command
# Lists all courses with given query in previous semester
# @history_group.command(name="search", description="Search courses in a previous semester by prefix/instructor/common core area!")
# async def history_search(interaction: discord.Interaction, query: str, semester_string: str) -> None:
#     await interaction.response.defer(thinking=True)

#     semester = get_quota.semester_string_to_code(semester_string)
#     if semester == -1:  # Error: invalid semester
#         await interaction.edit_original_response(content="⚠️ Invalid semester! Pick a semester from the autocomplete menu.")
#         return

#     cc_areas = get_quota.get_cc_areas(semester)
#     instructors = get_quota.get_attribute_list(3, semester) + get_quota.get_attribute_list(4, semester)

#     # Submit query to search function
#     embed_list = get_quota.compose_list(query, semester=semester)

#     # Error: Course data unavailable
#     if embed_list == "unavailable":
#         await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
#     # Error: invalid query
#     elif embed_list == "key":
#         await interaction.edit_original_response(content="⚠️ No courses found!")
#     else:
#         view = QuotaPage(mode="l", course_code=query, semester=semester)
#         await interaction.edit_original_response(embed=embed_list, view=view)

# Add command group to command tree
# bot.tree.add_command(history_group)

# "history" command group end

# "sub" command group
# List subscribed courses, subscribe to a course, unsubscribe from a course
subscribe_group = app_commands.Group(name="sub", description="Manage your course subscriptions!")

# "sub sub" command
@subscribe_group.command(description="Subscribe to a course! You'll be notified of its changes via DM.")
@app_commands.describe(course_code="Course code")
async def sub(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()
    embed_subscribe = get_quota.compose_subscribe(course_code, interaction.user.id, 0)

    # Error: Course data unavailable
    if embed_subscribe == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_subscribe == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    
    else:
        # Send confirmation/failure message
        await interaction.edit_original_response(embed=embed_subscribe)

        # Display message for new/canceled subscribers
        if_new_sub = get_quota.check_if_new_sub(interaction.user.id, 0)
        if if_new_sub != 1:
            embed_new_sub, view = get_quota.compose_new_sub_confirmation(if_new_sub)
            await interaction.channel.send(embed=embed_new_sub, view=view)

# "sub unsub" command
@subscribe_group.command(description="Unsubscribe from a course!")
@app_commands.describe(course_code="Course code")
async def unsub(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()

    # Detect unsubscribe all
    if course_code == "ALLCOURSES":
        operation = 2
    else:
        operation = 1
    
    embed_subscribe = get_quota.compose_subscribe(course_code, interaction.user.id, operation)

    # Error: Course data unavailable
    if embed_subscribe == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_subscribe == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    
    else:
        # Send confirmation/failure message
        await interaction.edit_original_response(embed=embed_subscribe)

        # Display message for new/canceled subscribers
        if_new_sub = get_quota.check_if_new_sub(interaction.user.id, 1)
        if if_new_sub != 1:
            embed_new_sub, view = get_quota.compose_new_sub_confirmation(if_new_sub)
            await interaction.channel.send(embed=embed_new_sub, view=view)

# "sub show" command
@subscribe_group.command(description="Show all courses you're subscribed to!")
async def show(interaction: discord.Interaction) -> None:
    await interaction.response.defer(thinking=True)

    # Send message of subscriptions
    embed_show = get_quota.compose_show(interaction)
    await interaction.edit_original_response(embed=embed_show)

    # Display message for new subscribers
    if_new_sub = get_quota.check_if_new_sub(interaction.user.id, 1)
    if if_new_sub != 1:
        embed_new_sub, view = get_quota.compose_new_sub_confirmation(if_new_sub)
        await interaction.channel.send(embed=embed_new_sub, view=view)

# Add "sub" command group to command tree
bot.tree.add_command(subscribe_group)

# "sub" command group end

# "about" command
# Show info about the bot
@bot.tree.command(description="Show info about the bot!")
async def about(interaction: discord.Interaction) -> None:
    await interaction.response.defer(thinking=True)

    guild_count = len(bot.guilds)
    embed_about = get_quota.compose_about(guild_count)

    try:
        view = QuotaPage(mode="a")
        view.clear_items()
        view.add_item(
            discord.ui.Button(
                label="Inspect my insides!",
                style=discord.ButtonStyle.link,
                emoji='🐙',
                url="https://github.com/succsuccsucc/tab-bot"
            )
        )
        await interaction.edit_original_response(embed=embed_about, view=view)
    except:
        await interaction.edit_original_response(content="⚠️ Error displaying about page!")
    
# Autocomplete current semester course codes
# @quota.autocomplete('course_code')
# @info.autocomplete('course_code')
# @sections.autocomplete('course_code')
@graph.autocomplete('course_code')  # hidden until hardware incompatibility resolved! 3/3
@sub.autocomplete('course_code')
async def sections_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    courses = get_quota.get_course_list()
    data = [app_commands.Choice(name=course, value=course)
            for course in courses if current.replace(" ", "").upper() in course.upper()
            ][0: 25]
    return data

# Autocomplete for `section` of "graph" command
@graph.autocomplete('section')
async def section_param_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    trend_db = TinyDB(f'tabtrend{get_quota.semester_code}.json', indent=4)  # Get database on demand to prevent outdated data
    data = []  # Return empty list if inputted course code doesn't match anything
    course_input = interaction.namespace.course_code  # Get current value in course_code field

    if course_input in trend_db.tables():  # Prevent creation of tables
        course_table = trend_db.table(course_input, cache_size=0)
        all_sections = course_table.all()
        all_sections = get_quota.get_field_data("section_code", all_sections)  # Extract section code
        all_sections = list(dict.fromkeys(all_sections))  # Remove duplicates
        data = [app_commands.Choice(name=section, value=section)
                for section in all_sections if current.replace(" ", "").upper() in section.upper()
                ][0: 25]
    
    return data

# Autocomplete all semesters course codes
# @history_quota.autocomplete('course_code')
# @history_sections.autocomplete('course_code')
# @history_info.autocomplete('course_code')
@quota.autocomplete('course_code')
@info.autocomplete('course_code')
@sections.autocomplete('course_code')
async def history_course_code_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    semester_list = get_quota.find_historical_data()

    courses = []
    for s in semester_list:  # Get previous semesters
        courses += get_quota.get_course_list(s)
    courses += get_quota.get_course_list()  # Get current semester
    courses = sorted(list(dict.fromkeys(courses)))  # Remove duplicates

    data = [app_commands.Choice(name=course, value=course)
            for course in courses if current.replace(" ", "").upper() in course.upper()
            ][0: 25]
    
    return data

# Autocomplete for `semester_name`
# @history_quota.autocomplete('semester_string')
# @history_sections.autocomplete('semester_string')
# @history_info.autocomplete('semester_string')
# @history_search.autocomplete('semester_string')
@quota.autocomplete('semester_name')
@info.autocomplete('semester_name')
@sections.autocomplete('semester_name')
@search.autocomplete('semester_name')
async def history_semester_string_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    semester_list = get_quota.find_historical_data()

    # Filter available semesters using the input query (course code or search query)
    if interaction.namespace.course_code:
        semester_list = [s for s in semester_list if interaction.namespace.course_code in get_quota.get_course_list(s)]
    elif interaction.namespace.query:
        semester_list = [s for s in semester_list if interaction.namespace.query in 
                           get_quota.get_prefix_list(s) 
                         + get_quota.get_attribute_list(3, s) 
                         + get_quota.get_attribute_list(4, s) 
                         + get_quota.get_cc_areas(s)]
    else:
        semester_list = []

    # Convert filename into semester names
    semester_list = [get_quota.semester_code_to_string(int(s)) for s in semester_list]

    data = [app_commands.Choice(name=semester_string, value=semester_string)
        for semester_string in semester_list if current.replace(" ", "").upper() in semester_string.upper()
        ][0: 25]
    return data

# Autocomplete for `semester` in /graph only
@graph.autocomplete('semester')
async def graph_history_semester_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    semester_list = plot_quota.find_historical_trends()[1: ]  # Remove current semester

    # Convert filename into semester names
    semester_list = [get_quota.semester_code_to_string(int(s)) for s in semester_list]

    data = [app_commands.Choice(name=semester_string, value=semester_string)
        for semester_string in semester_list if current.replace(" ", "").upper() in semester_string.upper()
        ][0: 25]
    return data

# Autocomplete for "sub unsub" command
@unsub.autocomplete('course_code')
async def unsub_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    # Get subscription list of current user
    subs, entry = get_quota.find_sub(interaction.user.id)
    courses = entry['courses']
    courses.append("All courses") # Add option to unsub from all courses
    # Turn them into command autocomplete options
    data = [app_commands.Choice(name=course, value=course)
    for course in courses if current.replace(" ", "").upper() in course.upper()
    ][0: 25]
    return data

# Get query from current semester
# @search.autocomplete('query')
async def search_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    prefix_list = get_quota.get_prefix_list()
    instructors = get_quota.get_attribute_list(3) + get_quota.get_attribute_list(4)
    cc_areas = get_quota.get_cc_areas()

    # Combine all lists into search suggestion
    prefix_list.extend(cc_areas)
    prefix_list.extend(instructors)

    data = [app_commands.Choice(name=query, value=query)
            for query in prefix_list if current.replace(" ", "").upper() in query.replace(" ", "").upper()
            ][0: 25]
    return data

# Autocomplete for `query` of "history search" command group
# Get query from all semesters
# @history_search.autocomplete('query')
@search.autocomplete('query')
async def history_query_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    semester_list = get_quota.find_historical_data()
    semester_list.append("")  # Include current semester

    queries = []
    for s in semester_list:  # Previous semesters + current semester
        queries.extend(get_quota.get_prefix_list(s))
        queries.extend(get_quota.get_attribute_list(3, s) + get_quota.get_attribute_list(4, s))
        queries.extend(get_quota.get_cc_areas(s))
    queries = list(dict.fromkeys(queries))  # Remove duplicates

    data = [
        app_commands.Choice(name=query, value=query)
        for query in queries if current.replace(" ", "").upper() in query.replace(" ", "").upper()
    ][0: 25]
    return data

# Autocomplete for `room` of "room schedule" command
# Get list of rooms
@room_schedule.autocomplete('room')
async def room_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    rooms = get_quota.get_attribute_list(2)
    data = [
        app_commands.Choice(name=room, value=room)
        for room in rooms if current.replace(" ", "").upper() in room.replace(" ", "").upper()
    ][0: 25]
    return data

# "debug" command
# Upload bot and quota status to Discord for remote debug
# Only available in test server
@bot.tree.command(description="Upload bot and quota status for debug!", guild=discord.Object(test_server_id))
@app_commands.describe(file="Name of the file to upload")
async def debug(interaction: discord.Interaction, file: str) -> None:
    await interaction.response.defer(thinking=True)

    if interaction.user.id != admin_id:
        await interaction.edit_original_response(content="🚫 This command can only be ran by the admin!")
        return

    # Send list of connected servers
    if file == "guild_list":
        # Put list of guilds into txt file
        guild_list_file = open('guild_list.txt', 'w')
        for guild in bot.guilds:
            guild_list_file.write(f'{guild.name}(id: {guild.id})\n')
        guild_list_file.close()

        # Send the txt file
        await interaction.edit_original_response(content=f"🎏 Bot is connected to {len(bot.guilds)} servers!")
        await interaction.channel.send(file=discord.File("guild_list.txt"))

        # Delete the txt file
        try:
            os.remove("guild_list.txt")
        except:
            pass
    
    # Send quotas file scraped by the bot
    else:
        # Send trends file
        if file == "tabtrend":
            file = f"{file}{get_quota.semester_code}"
        await interaction.edit_original_response(content=f"🎏 Quotas file: `{file}.json`")
        await interaction.channel.send(file=discord.File(f"{file}.json"))

@debug.autocomplete('file')
async def debug_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    file_list = ['quotas', 'quotas_old', 'subscribers', 'guild_list', 'tabtrend']
    file_list = [app_commands.Choice(name=file, value=file) for file in file_list if current.upper() in file.upper()]
    return file_list

# "leave" command
# Remove the bot from a server
@bot.tree.command(description="Remove the bot from a server!", guild=discord.Object(test_server_id))
async def leave(interaction: discord.Interaction, id: str) -> None:
    await interaction.response.defer(thinking=True)

    if interaction.user.id != admin_id:
        await interaction.edit_original_response(content="🚫 This command can only be ran by the admin!")
        return

    try:
        await bot.get_guild(int(id)).leave()
        await interaction.edit_original_response(content=f"🙋‍♀️ Left server with ID: {id})!")
    except:
        await interaction.edit_original_response(content=f"🤷‍♀️ Bot not in server!")

# Slash commands end

# Text commands start
# "sync" command
# Syncs command tree with Discord
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
