# get_quota.py
import requests  # Requires requests 2.29.0!
import bs4

import discord

import os
import json
from datetime import datetime, timezone
import re
import traceback

import config
import subject_channels

# Change working directory to wherever this is in
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# semester code of course quota website
# first 2 digits correspond to the year
# Last 2 digits correspond to season
# Fall: 10
# Winter: 20
# Spring: 30
# Summer: 40
semester_code = 2310  # 23-24 Fall

def trim_section(section_code):
    section_trim = re.findall("[A-Z]+[0-9]*[A-Z]*", section_code)[0]
    return section_trim

# Store current time (UTC) as last updated time when quota update is finished
def update_time():
    now = datetime.now(timezone.utc)
    date_time = int(datetime.timestamp(now))
    return date_time

# Convert time string formatted by update_time() to Discord timestamp
# List of styles: https://gist.github.com/LeviSnoot/d9147767abeef2f770e9ddcd91eb85aa
def disc_time(stamp, style=""):
    time_string = f"<t:{stamp}:{style}>"
    return time_string

# Convert timestamp to plain text timestamp
# Uses local timezone
def text_time(stamp):
    now = datetime.fromtimestamp(stamp)
    time_text = now.strftime("%H:%M:%S")
    return time_text

# Convert UNIX timestamp to aware datetime object (UTC)
def time_from_stamp(stamp):
    time_object = datetime.fromtimestamp(stamp, timezone.utc)
    return time_object

# Find additions and removals between two lists
def list_diffs(temp1, temp2):
    additions = [x for x in temp1 if x not in set(temp2)]  # Elements in temp1 not in temp2
    removals = [x for x in temp2 if x not in set(temp1)]  # Elements in temp2 not in temp1
    return additions, removals  # Returns a tuple (additions, removals)

# Add diff highlighting to a list of strings
# Calls list_diffs() to find diffs
def diff_highlight(new, old):
    diff_tuple = list_diffs(new, old)
    new = [("+" + x.replace("\n", "\n+")) if x in diff_tuple[0] else (" " + x.replace("\n", "\n ")) for x in new]
    old = [("-" + x.replace("\n", "\n-")) if x in diff_tuple[1] else (" " + x.replace("\n", "\n ")) for x in old]
    return new, old  # Returns a tuple of new, old with diff highlighting

# Find section matching message in a course
def find_sect_matching(course_dict):
    sect_matching = None
    if "MATCHING" in course_dict['info'].keys():
        sect_matching = "ℹ️ " + course_dict['info']['MATCHING'].strip("[]")
    return sect_matching

# Get source URL on original UST course quota website for "Source" button
def get_source_url(course_code, mode=None):
    if mode == "l":  # /list command, link to top of website
        source_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/subject/{course_code}"
    else:
        source_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/subject/{course_code[0: 4]}#{course_code}"
    return source_url

# Dict containing all subject channels
channels = None
async def get_channels(bot):
    global channels
    channels = await subject_channels.find_channels(bot)

# Send error message during quota update loop
async def send_loop_exception(current_loop, error_type, error_msg):
    await channels.get("error").send(f"👺 Error in quota update loop `{current_loop}`:\n{error_type}```\n{error_msg}\n```")

# Get list of all course codes
def get_course_list():
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return []
    
    courses = list(quotas.keys())
    courses.remove('time')  # Remove update time entry
    return courses

# Get list of all course code prefixes
def get_prefix_list():
    # Get course list
    courses = get_course_list()

    # Trim all course codes to prefix only
    prefix_list = [x[0: 4] for x in courses]  # All prefixes are 4 letters long
    # Remove duplicates
    prefix_list = list(dict.fromkeys(prefix_list))

    return prefix_list

# Get list of all common core areas
def get_cc_areas():
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return []
    
    # Remove update time entry
    quotas.pop("time")  

    cc_areas = [x['info']['ATTRIBUTES'] for x in quotas.values() if 'ATTRIBUTES' in x['info']]
    # Split attributes lines
    cc_areas = sum([y.split("\n") for y in cc_areas], [])
    # Remove duplicates
    cc_areas = list(dict.fromkeys(cc_areas))
    # Remove non CC attributes
    cc_areas = [z for z in cc_areas if "Common Core" in z]

    return cc_areas

# Get subscribers file
def open_subs():
    try:
        subs = open('subscribers.json', encoding='utf-8')
        subs = json.load(subs)
        return subs
    except FileNotFoundError:  # Create empty subscribers file (dict) if it is not found
        subs = {}
        save_subs(subs)
        return subs

# Save the edited subscribers file
def save_subs(subs):
    outfile = open('subscribers.json', 'w', encoding='utf-8')
    json.dump(subs, outfile, indent=4)
    return subs

# Add a new user to the subscribers file
# Only called when they are not on the file
def new_profile(subs, id):
    # Initialize entry for new user
    new_user = {
        "confirm": 0,
        "strikes": 0,
        "courses": []
    }

    # Add the user to dict of subscribers
    subs[str(id)] = new_user
    subs = save_subs(subs)
    return subs

# Find entry of user in subscribers dict
def find_sub(id):
    subs = open_subs()
    entry = subs.get(str(id), None)

    # Create new profile for user if they're not found in subscribers dict
    if not entry:
        subs = new_profile(subs, id)
        entry = subs.get(str(id), None)
    
    return subs, entry

# Edit list of courses a subscriber is subscribed to
#
# operation: can be subscribe (0) or unsubscribe (1)
# course_code: Course code to be added to course list of subscriber
# idx: index in course list to be removed
#
def edit_sub(id, operation, course_code=None):
    # Get subscriber entry and subscribers dict
    subs, entry = find_sub(id)

    # Add a course to course list of subscriber (subscribe)
    if operation == 0:
        # User cannot subscribe to more than 10 courses
        if len(entry['courses']) >= 10:
            return 1
        # User cannot subscribe to the same course twice
        elif course_code in entry['courses']:
            return 3
        else:
            entry['courses'].append(course_code)
    
    # Remove a course from the course list (unsubscribe)
    else:
        try:
            entry['courses'].remove(course_code)
        except ValueError:
            return 2
    
    # Save the edited subscribers list
    save_subs(subs)
    return 0

# Check if user is a new/canceled subscriber (value of key "confirm" is 0/2)
def check_if_new_sub(id, mode):
    subs, entry = find_sub(id)

    # Subscribing after canceled: reset status and send warning message
    # Only reset status when subscribing
    if entry['confirm'] == 2 and mode == 0:
        entry['confirm'] = 0
        save_subs(subs)
        return 2
    else:
        return entry['confirm']

# Check if user is subscribed to a given course
def check_if_subscribed(course_code, id):
    subs, entry = find_sub(id)

    if course_code in entry['courses']:
        return True
    else:
        return False

def open_quotas():
    try:
        quotas = open('quotas.json', encoding='utf-8')
        quotas = json.load(quotas)
        return quotas
    except:
        return False

def open_old_quotas():
    try:
        quotas = open('quotas_old.json', encoding='utf-8')
        quotas = json.load(quotas)
        return quotas
    except:
        return False

# If quota searching is interrupted by network issues, quotas file is incomplete and does not contain the update time
def check_quotas_validity():
    quotas = open_quotas()
    if not quotas:
        return False
    try:
        if 'time' in quotas:
            return True
        else:
            return False
    except TypeError:  # Error raised if quotas file is corrupted
        return False

# Send message if course data is unavailable
embed_quota_unavailable = discord.Embed(title=f"⚠️ Course data is unavailable at the moment!",
                                        description="Try again in a minute.",
                                        color=config.color_failure)

# Calculate max page index
def find_max_page(dict, page_size):
    max_page = int(len(dict) / page_size)
    # Error: a course has no sections
    if len(dict) == 0:
        return -1
    # Edge case: number of sections is non-zero multiple of page size
    elif len(dict) % page_size == 0:
        max_page -= 1

    return max_page

# Compose message of course quotas for "quota" command
def compose_message(course_code, page=0):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"

    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    # Calculate max page index
    page_size = 10
    max_page = find_max_page(course_dict['sections'], page_size)

    # Send error message if there is no sections (highly unlikely)
    if max_page == -1:
        return "no_sections"

    # Check if page number is valid
    if page < 0:
        return "p0"
    elif page > max_page:
        return "pmax"

    # Cut out one page of data
    try:
        sections_paged = list(course_dict['sections'].items())[page_size * page: page_size * (page + 1)]
    except IndexError:
        sections_paged = list(course_dict['sections'].items())[page_size * page: ]

    # Include section matching message if there is one
    sect_matching = find_sect_matching(course_dict)
    
    # Compose list
    embed_quota = discord.Embed(title=f"{course_dict['title']}",
                                description=sect_matching,
                                color=config.color_success,
                                timestamp=time_from_stamp(quotas['time']))  # Quota update time

    quota_field = f"```ansi\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"

    for key, value in sections_paged:
        quota_field += f"{trim_section(key):<8}| "
        
        # Total quotas
        for i in range(4, 8):
            quota_field += '{:<6}'.format(value[i].split("\n")[0])
        quota_field += "\n"

        # Check for reserved quotas
        quota_of_section = value[4].split("\n")
        # If there is reserved quotas, display in next line
        if len(quota_of_section) >= 3:
            for k in range(2, len(quota_of_section)):
            # Split dept name and quota/enrol/avail
                reserved_quotas = quota_of_section[k].split(": ")
                reserved_quotas_dept = reserved_quotas[0]  # dept part
                reserved_quotas_qea = reserved_quotas[1].split("/")  # quota/enrol/avail part

                # Display reserved quotas
                # Show that quotas are reserved
                quota_field += f"\u001b[0;41;37m> {'Res.':<6}| "  # Discord ANSI: https://gist.github.com/kkrypt0nn/a02506f3712ff2d1c8ca7c9e0aed7c06
                # quota/enrol/avail
                for j in range(3):
                    quota_field += "{:<6}".format(reserved_quotas_qea[j])
                # dept
                quota_field += f"For: {reserved_quotas_dept}"
                quota_field += "\u001b[0m\n"

    quota_field += "```"

    embed_quota.add_field(name="🍊 Sections", value=quota_field, inline=False)

    # Embed timestamp (update time) is shown behind footer
    embed_quota.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated")
    embed_quota.set_author(name="🍊 Quotas of")

    return embed_quota

# Compose message of course info for "info" command
def compose_info(course_code):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    embed_info = discord.Embed(title=f"{course_dict['title']}",
                               color=config.color_success,
                               timestamp=time_from_stamp(quotas['time']))  # Quota update time
    
    for key, value in course_dict['info'].items():
        # Skip section matching message
        if key == "MATCHING":
            continue

        key = key.capitalize()
        key = key.replace("\n", " ")

        # Split info into multiple fields
        for chunk in range(int(len(value) / 1024) + 1):
            if chunk == 0:
                field_title = f"🍊 {key}"
            else:
                field_title = f"🍊 {key} (cont.)"

            try:
                embed_info.add_field(name=field_title, value=value[1024 * chunk: 1024 * (chunk + 1)], inline=False)
            except IndexError:
                embed_info.add_field(name=field_title, value=value[1024 * chunk: ], inline=False)

    embed_info.set_footer(text=f"🕒 Last updated")
    embed_info.set_author(name="🍊 Information about")

    return embed_info

# Compose message of course sections, instructors, schedules for "sections" command
def compose_sections(course_code, page=0):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    # Include section matching message if there is one
    sect_matching = find_sect_matching(course_dict)
    
    embed_sections = discord.Embed(title=f"{course_dict['title']}",
                                   description=sect_matching,
                                   color=config.color_success,
                                   timestamp=time_from_stamp(quotas['time']))  # Quota update time
    
    # Calculate max page index
    page_size = 5
    max_page = find_max_page(course_dict['sections'], page_size)

    # Send error message if there is no sections
    if max_page == -1:
        return "no_sections"

    # Check if page number is valid
    if page < 0:
        return "p0"
    elif page > max_page:
        return "pmax"
    
    # Cut out one page of data
    try:
        sections_paged = list(course_dict['sections'].items())[page_size * page: page_size * (page + 1)]
    except IndexError:
        sections_paged = list(course_dict['sections'].items())[page_size * page: ]

    for key, value in sections_paged:
        section_id = key
        section_field = "```ansi\n"  # Use ANSI text coloring

        time_list = value[1].split("\n\n\n")
        venue_list = value[2].split("\n\n\n")
        instructor_list = value[3].split("\n\n\n")

        # Make all strings single-line
        time_list = [t.replace('\n', ', ') for t in time_list]
        venue_list = [t.replace('\n', ', ') for t in venue_list]
        instructor_list = [t.replace('\n', ', ') for t in instructor_list]

        # Add strings to field
        # Add strings row by row
        for i in range(len(time_list)):
            # Field character limit protection: buffer new rows
            section_field_pending = ""

            section_field_pending += f"{'Time':<6}| {time_list[i]}\n"
            section_field_pending += f"{'Venue':<6}| {venue_list[i]}\n"
            section_field_pending += f"{'By':<6}| {instructor_list[i]}\n"
            section_field_pending += "\n"

            # Count chars before adding to field
            if len(section_field) + len(section_field_pending) > 1020:  # end of codeblock is 4 chars long
                # Send current block to field first
                section_field += "\n```"
                embed_sections.add_field(name=f"🍊 {key}",
                                 value=section_field,
                                 inline=False)
                # Reset field for next block
                section_field = "```\n" + section_field_pending
            else:  # Char count under limit: add new row to field
                section_field += section_field_pending

        # Buffer remarks
        section_field_pending = ""

        # Add remarks
        # There will always be at most 1 remark per section
        if value[8] != "\u00a0":  # Only make space if remarks field is non-empty
            # Split remarks into lines to remove redundant newlines
            remarks_list_unfiltered = value[8].split("\n")
            # Remove empty lines
            remarks_list = [x for x in remarks_list_unfiltered if x != '' and x != '\xa0']
            # Display the remarks
            section_field_pending += "Remarks:\n"  
            #section_field += "\u001b[0;41;37m" #  Coloring start: Orange background, white text
            section_field_pending += "\n".join(remarks_list)
            #section_field += "\u001b[0m"  # Coloring end
            section_field_pending += "\n"

        # Field character limit protection: count chars before adding remarks
        if len(section_field) + len(section_field_pending) > 1020:
            # Send current block to field first
            section_field += "\n```"
            embed_sections.add_field(name=f"🍊 {key}",
                                 value=section_field,
                                 inline=False)
            # Reset field for next block
            section_field = "```\n" + section_field_pending
        else:  # Char count under limit: add remarks to field
            section_field += section_field_pending

        section_field += "```"
        embed_sections.add_field(name=f"🍊 {key}",
                                 value=section_field,
                                 inline=False)

    # Embed timestamp (update time) is shown behind footer
    embed_sections.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated")
    embed_sections.set_author(name="🍊 Sections of")

    return embed_sections

# Compose message of all courses with given prefix for "list" command
def compose_list(prefix, page=0):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"  # Error code: quotas file is unavailable
    
    # Get list of common core areas
    cc_areas = get_cc_areas()

    # Check if prefix is valid
    prefix_list = get_prefix_list()
    if (prefix not in prefix_list) and (prefix not in cc_areas):
        return "key"  # Error code: prefix is invalid
    
    # Get dict of all courses with prefix/CC area
    if prefix in cc_areas:
        prefix_courses = {k: v for k, v in quotas.items() if k != "time" and prefix in v.get('info').get('ATTRIBUTES', '')}
        list_title = prefix.replace("Common Core", "")  # "Common Core" will be displayed in header (author)
        list_header = "🍊 Common Core courses in"  # Embed header (author) text
    else:
        prefix_courses = {k: v for k, v in quotas.items() if prefix in k}
        list_title = prefix  # Change nothing
        list_header = "🍊 Courses with prefix"

    # Prepare embed to display courses in
    embed_list = discord.Embed(title=list_title,
                               color=config.color_success,
                               timestamp=time_from_stamp(quotas['time']))  # Quota update time

    # Calculate max page index
    page_size = 5
    max_page = find_max_page(prefix_courses, page_size)

    # Check if page number is valid
    if page < 0:
        return "p0"  # Error code: first page reached
    elif page > max_page:
        return "pmax"  # Error code: last page reached
    
    # Cut out one page of data
    try:
        list_paged = list(prefix_courses.items())[page_size * page: page_size * (page + 1)]
    except IndexError:
        list_paged = list(prefix.items())[page_size * page: ]
    
    # Format the data into the embed
    for key, value in list_paged:
        course_code = value['title'][0: 10]  # Course codes are max 9 chars long and followed by a space
        course_title = value['title'][12: ]  # Course titles have 1 leading space

        # Add course to embed as field
        embed_list.add_field(name=f"🍊 {course_code}",
                             value=course_title,
                             inline=False
        )
    
    # Embed timestamp (update time) is shown behind footer
    embed_list.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated")
    # Header message
    embed_list.set_author(name=list_header)

    return embed_list

# Display user's subscriptions for "sub" group commands
def display_subscriptions(id):
    subs, entry = find_sub(id)

    # Prepare string for list of subscribed courses
    subscriptions = "```\n"
    # Add courses to string
    for count, course in enumerate(entry['courses'], 1):
        subscriptions += f"{count}. {course}\n"
    # Finish the string
    subscriptions += "```"

    return subscriptions

# Subscribe to a course for "subscribe" command
# operation: 0 for subscribe, 1 for unsubscribe
def compose_subscribe(course_code, id, operation):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        if check_if_subscribed(course_code, id):  # Allow command to proceed if course code is subscribed (course is deleted by HKUST)
            pass
        else:
            return "key"
    else:
        if course_code == "time":
            return "key"
    
    # Attempt to subscribe/unsubscribe
    sub_result = edit_sub(id, operation=operation, course_code=course_code)

    # Footer: only shown when successfully subscribing to a course
    sub_embed_footer = None

    # Decide embed author depending on operation
    if operation == 0:
        sub_embed_author = "🎏 Successfully subscribed to"
        sub_embed_footer = "🎏 Tab will notify you via DM when there are changes to the above courses!"  # Only shown when successfully subscribing
    else:
        sub_embed_author = "🎏 Successfully unsubscribed from"
    # Set embed color to success
    sub_embed_color = config.color_success
    # Success: no reason for failure
    sub_failed_reason = None

    if sub_result != 0:
        # Decide embed author depending on operation
        if operation == 0:
            sub_embed_author = "⚠️ Failed to subscribe to"
            sub_embed_footer = None  # Failed to subscribe: no footer
        else:
            sub_embed_author = "⚠️ Failed to unsubscribe from"
        # Set embed color to failure
        sub_embed_color = config.color_failure
        # Show reason for sub/unsub failure
        if sub_result == 1:
            sub_failed_reason = "You cannot subscribe to more than 10 courses!"
        elif sub_result == 2:
            sub_failed_reason = "You're not subscribed to this course!"
        elif sub_result == 3:
            sub_failed_reason = "You're already subscribed to the course!"
    
    # Prepare embed title in case course is deleted
    try:
        sub_embed_title = course_dict['title']
    except:
        sub_embed_title = course_code

    # Prepare embed
    embed_subscribe = discord.Embed(
        title=sub_embed_title,
        description=sub_failed_reason,
        color=sub_embed_color
    )

    # Add subscription list to embed
    subscriptions = display_subscriptions(id)
    embed_subscribe.add_field(
        name="🎏 Your subscriptions",
        value=subscriptions,
        inline=False
    )

    # Set author and footer field
    embed_subscribe.set_author(name=sub_embed_author)
    embed_subscribe.set_footer(text=sub_embed_footer)

    return embed_subscribe

# Compose message of user's subscriptions for "sub show" command
def compose_show(interaction):
    # Get list of user's subscriptions
    subscriptions = display_subscriptions(interaction.user.id)

    # Prepare embed
    embed_show = discord.Embed(
        title="Your subscriptions",
        color=config.color_info
    )

    # Set author field
    embed_show.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    # Add subscription list to embed
    embed_show.add_field(
        name=f"🎏 Courses",
        value=subscriptions,
        inline=False
    )

    # Add footer
    embed_show.set_footer(text="🎏 Tab will notify you via DM when there are changes to the above courses!")

    return embed_show

# Compose DM permission tutorial link for "sub" group commands
class SubLinks(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

# Display message for new/canceled subscribers for "sub" group commands
def compose_new_sub_confirmation(mode):
    embed_strings = {
        0: [
            "Your subscription is pending! Please wait for verification.",  # Embed title
            "To conserve resources, we need to make sure you can actually receive Tab's notifications before you can subscribe. Normally you'll only need to verify once!",  # Embed description
            config.color_info,  # Embed color
            "🎏 Howdy new subscriber!",  # Author
            "🎏 How to verify?",  # Field 1 name
            "Tab will send you a confirmation DM within 5 minutes. Once you receive it, you're verified and can subscribe freely! Your current subscriptions will also be saved. This process is automatic and no action is needed!",  # Field 1 value
            "🎏 What to do if I didn't receive the DM?",  # Field 2 name
            "1. **Join our server**\nBy default, Discord only allows DMs from users sharing a mutual server with you. Since Tab only resides in our server, you should join it to give Tab sufficient permissions to DM you!\n2. **Check your privacy settings**\nCheck if you blocked DMs from members of our server! See how to do it in the article linked below.\n3. **Subscribe again**\nTab will cancel your subscriptions after 3 failed attempts to DM you. After checking your privacy settings, you should subscribe again!"  # Field 2 value
        ],
        2: [
            "Verification failed! Please check your privacy settings.",
            "Your subscription has been canceled. If you're resubscribing, a new confirmation DM is on its way!",
            config.color_failure,
            "⚠️ Tab couldn't reach you!",
            "🎏 What should I do now?",
            "1. **Join our server**\nBy default, Discord only allows DMs from users sharing a mutual server with you. Since Tab only resides in our server, you should join it to give Tab sufficient permissions to DM you!\n2. **Check your privacy settings**\nCheck if you blocked DMs from members of our server! See how to do it in the article linked below.\n3. **Subscribe again**\nYour subscriptions have been canceled for now. After checking your privacy settings, you should subscribe again if you haven't!",
            None,
            None
        ]
    }

    # Create the embed
    embed_new_sub = discord.Embed(
        title=embed_strings[mode][0],
        description=embed_strings[mode][1],
        color=embed_strings[mode][2]
    )

    # Set embed author
    embed_new_sub.set_author(name=embed_strings[mode][3])

    # Add message body
    embed_new_sub.add_field(
        name=embed_strings[mode][4],
        value=embed_strings[mode][5],
        inline=False
    )
    if mode == 0:
        embed_new_sub.add_field(
            name=embed_strings[mode][6],
            value=embed_strings[mode][7],
            inline=False
        )

    # Add links to "UST Course Qutoas" server and Discord article on privacy settings
    view = SubLinks()
    view.add_item(discord.ui.Button(label="🍊 Join our server!", style=discord.ButtonStyle.link, url="https://discord.gg/RNmMMF6xHY"))
    view.add_item(discord.ui.Button(label="📙 Learn about DM privacy settings", style=discord.ButtonStyle.link, url="https://support.discord.com/hc/en-us/articles/217916488-Blocking-Privacy-Settings-"))

    return embed_new_sub, view

# Send confirmation DMs to new subscribers after every update loop
# Unsubscribe users with 3 strikes (failed DMs)
async def check_on_everyone(bot):
    # Get subscribers file
    subs = open_subs()

    # Scan all subscribers for new subscribers
    for key, value in subs.items():
        # New subscriber found: attempt to confirm them
        if value['confirm'] == 0:  
            # Get list of subscriptions of user
            subscriptions = display_subscriptions(key)

            # Prepare embed
            embed_confirmation_dm = discord.Embed(
                title="Verification complete! Your subscription is confirmed.",
                color=config.color_success
            )

            # Set author
            embed_confirmation_dm.set_author(name="🎏 Confirmation DM sent successfully!")

            # Add subscription list to embed
            embed_confirmation_dm.add_field(
                name="🎏 Your subscriptions",
                value=subscriptions,
                inline=False
            )

            # Set footer
            embed_confirmation_dm.set_footer(text="🎏 Tab will notify you via DM when there are changes to the above courses!")

            # Attempt to send the DM
            try:
                await bot.get_user(int(key)).send(embed=embed_confirmation_dm)
            except discord.errors.Forbidden:  # Only strike when Discord blocked the DM
                value['strikes'] += 1  # Failed to message once: Strike
            else:
                value['confirm'] = 1  # DM success: confirm
        
        # Subscriber with 3 strikes found: unsubscribe them
        if value['strikes'] >= 3:
            value['courses'] = []  # Unsubscribe them
            value['confirm'] = 2  # Set status to "unsubscribed"
            value['strikes'] = 0  # Reset number of strikes
    
    save_subs(subs)

# Send course changes to subscribers
async def send_to_subscribers(bot, course_code, embed):
    # Get subscribers file
    subs = open_subs()

    # Check all subscribers for subscribers to the course
    # Must also be verified (confirmed)
    for key, value in subs.items():
        if course_code in value['courses'] and value['confirm'] == 1 and value['strikes'] < 3:
            # Attempt to send the DM
            try:
                await bot.get_user(int(key)).send(embed=embed)
            except discord.errors.Forbidden:
                value['strikes'] += 1  # Failed to message once: Strike
            except ValueError:  # Stop bot from freaking out over oversized embed (unlikely)
                pass
    
    # Save subscribers file after striking users
    save_subs(subs)

# Helper function to check if course/section/quota changed
async def check_diffs(bot, new_quotas=None, old_quotas=None):
    # Open quotas files
    if not new_quotas:
        new_quotas = open_quotas()
    if not old_quotas:
        old_quotas = open('quotas_old.json', encoding='utf-8')
        try:
            old_quotas = json.load(old_quotas)
        except:
            print("Old quotas file corrupted! Restart the bot.")
            return

    # No comparison if current quotas file or last quotas file is corrupted
    if (not check_quotas_validity()) or (old_quotas == {}) or ('time' not in new_quotas):
        return
    
    changed = False
    for key, value in new_quotas.items():
        # Skip 'time' entry
        if key == 'time':
            continue

        # 🥑 New course!
        if key not in old_quotas:
            # await channels.get(key[0: 4], channels['other']).send(f"🥑 **New course!**\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
            # Prepare change announcement embed: course name
            embed_new_course = discord.Embed(
                title=f"{value.get('title', 'Error')}",
                color=0x8bd5ca  # Teal
            )
            # Prepare header of change announcement
            embed_new_course.set_author(name="🥑 New course!")

            # Display list of sections
            new_course_sections = "```\n"
            new_course_sections += "\n".join(list(value['sections'].keys()))
            new_course_sections += "\n```"

            # Add field
            embed_new_course.add_field(
                name=f"🥑 {len(value['sections'])} sections",
                value=new_course_sections,
                inline=False
            )

            # Send the announcement
            await channels.get(key[0: 4], channels['other']).send(embed=embed_new_course)
            await send_to_subscribers(bot, key, embed_new_course)
            changed = True

        else:
            # 🥥 Course info changed!
            # Initialize dicts of course info
            info_compare_old = old_quotas[key]['info']
            info_compare_new = new_quotas[key]['info']

            # Check course info additions and changes
            for k, v in info_compare_new.items():
                # Send 1 message for every change
                embed_course_info_change = discord.Embed(
                    title=f"{value.get('title', 'Error')}",
                    color=0xcad3f5  # Text
                )
                embed_course_info_change.set_author(name="🥥 Course info changed!")

                # Send message for new course info
                if k not in info_compare_old:
                    # Split info into multiple fields
                    for v_chunk in range(int(len(v) / 1014) + 1):  # Leave room for MD codeblock characters
                        if v_chunk == 0:
                            k_name = "🥥 New: " + k.replace("\n", " ").capitalize()
                        else:
                            k_name = k.replace("\n", " ").capitalize() + " (cont.)"
                        
                        try:
                            embed_course_info_change.add_field(
                                name=k_name,
                                value=f"```\n{v[1014 * v_chunk: 1014 * (v_chunk + 1)]}\n```",
                                inline=False
                            )
                        except IndexError:
                            embed_course_info_change.add_field(
                                name=k_name,
                                value=f"```\n{v[1014 * v_chunk: ]}\n```",
                                inline=False
                            )

                    # Send the message
                    try:
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_course_info_change)
                    except ValueError:  # Stop bot from freaking out over oversized embed (unlikely)
                        pass
                    await send_to_subscribers(bot, key, embed_course_info_change)
                    changed = True

                # Send message for changed course info
                elif v != info_compare_old[k]:
                    # Split info into multiple fields
                    for piece_k, piece_v in {"⬅️ Old": info_compare_old[k], "➡️ New": v}.items():
                        for v_chunk in range(int(len(piece_v) / 1014) + 1):
                            piece_k_name = ""
                            # "Heading": Display part of course info changed
                            if piece_k == "⬅️ Old" and v_chunk == 0:
                                piece_k_name = "🥥 Changed: " + k.replace("\n", " ").capitalize() + "\n"
                            piece_k_name += piece_k
                            if v_chunk > 0:
                                piece_k_name += " (cont.)"
                            
                            try:
                                embed_course_info_change.add_field(
                                    name=piece_k_name,
                                    value=f"```\n{piece_v[1014 * v_chunk: 1014 * (v_chunk + 1)]}\n```",
                                    inline=False
                                )
                            except IndexError:
                                embed_course_info_change.add_field(
                                    name=piece_k_name,
                                    value=f"```\n{piece_v[1014 * v_chunk: ]}\n```",
                                    inline=False
                                )
                        
                    # Send the message
                    try:
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_course_info_change)
                    except ValueError:  # Stop bot from freaking out over oversized embed (unlikely)
                        pass
                    await send_to_subscribers(bot, key, embed_course_info_change)
                    changed = True
                
            # Check course info removals
            for k, v in info_compare_old.items():
                # Send 1 message for every removal
                embed_course_info_change = discord.Embed(
                    title=f"{value.get('title', 'Error')}",
                    color=0xcad3f5  # Text
                )
                embed_course_info_change.set_author(name="🥥 Course info changed!")

                # Send message for removed course info
                if k not in info_compare_new:
                    # Split info into multiple fields
                    for v_chunk in range(int(len(v) / 1014) + 1):  # Leave room for MD codeblock characters
                        if v_chunk == 0:
                            k_name = "🥥 Removed: " + k.replace("\n", " ").capitalize()
                        else:
                            k_name = k.replace("\n", " ") + " (cont.)"
                        
                        try:
                            embed_course_info_change.add_field(
                                name=k_name,
                                value=f"```\n{v[1014 * v_chunk: 1014 * (v_chunk + 1)]}\n```",
                                inline=False
                            )
                        except IndexError:
                            embed_course_info_change.add_field(
                                name=k_name,
                                value=f"```\n{v[1014 * v_chunk: ]}\n```",
                                inline=False
                            )

                    # Send the message
                    try:
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_course_info_change)
                    except ValueError:  # Stop bot from freaking out over oversized embed (unlikely)
                        pass
                    await send_to_subscribers(bot, key, embed_course_info_change)
                    changed = True

            for key2, value2 in value['sections'].items():
                # 🍅 New section!
                if key2 not in old_quotas[key]['sections']:
                    # Quota of the new section
                    quota_new = value2[4].split("\n")
                    # await channels.get(key[0: 4], channels['other']).send(f"🍅 **New section!**\n{value.get('title', 'Error')}: {key2}\nQuota: {quota_new}")
                    
                    # Prepare change announcement embed: course name, section name
                    embed_new_section = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xed8796  # Red
                    )
                    # Prepare header of change announcement
                    embed_new_section.set_author(name="🍅 New section!")

                    # Display quota of section: Total
                    new_section_quotas = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
                    new_section_quotas += f"{trim_section(key2):<8}| "
                    for i in range(4, 8):
                        new_section_quotas += '{:<6}'.format(value2[i].split("\n")[0])
                    
                    # Display quota of section: reserved
                    new_res_dict = {}
                    if len(quota_new) >= 3:
                        # Dict to store dept names and numbers
                        for i in range(2, len(quota_new)):
                            # Split dept name from numbers
                            quota_new_res = quota_new[i].split(": ")
                            new_res_dict[quota_new_res[0]] = quota_new_res[1].split("/")
                    
                    for k, v in new_res_dict.items():
                        new_section_quotas += f"\n{'> Res.':<8}| "
                        # Quota/enrol/avail
                        for i in range(3):
                            new_section_quotas += f"{v[i]:<6}"
                        # Dept
                        new_section_quotas += f"For: {k}"

                    new_section_quotas += "\n```"

                    # Add field
                    embed_new_section.add_field(
                        name="🍅 Quota",
                        value=new_section_quotas,
                        inline=False
                    )
                    
                    # Send the announcement
                    await channels.get(key[0: 4], channels['other']).send(embed=embed_new_section)
                    await send_to_subscribers(bot, key, embed_new_section)
                    changed = True
                
                else:
                    # 🍋 Quota changed!
                    quota_section_old = old_quotas[key]['sections'][key2][4].split("\n")
                    quota_section_new = value2[4].split("\n")

                    # Total quota
                    quota_old = quota_section_old[0]
                    quota_new = quota_section_new[0]

                    # Reserved quota (if exists)
                    # Old
                    quota_res_old_dict = {}
                    if len(quota_section_old) >= 3:
                        # Dict to store dept names and numbers
                        for i in range(2, len(quota_section_old)):
                            # Split dept name from numbers
                            quota_res_old = quota_section_old[i].split(": ")
                            quota_res_old_dict[quota_res_old[0]] = quota_res_old[1].split("/")
                    
                    # New
                    quota_res_new_dict = {}
                    if len(quota_section_new) >= 3:
                        # Dict to store dept names and numbers
                        for i in range(2, len(quota_section_new)):
                            # Split dept name from numbers
                            quota_res_new = quota_section_new[i].split(": ")
                            quota_res_new_dict[quota_res_new[0]] = quota_res_new[1].split("/")

                    # Check if reserved quotas changed
                    quota_res_old_compare = {}
                    quota_res_new_compare = {}
                    for k, v in quota_res_old_dict.items():
                        quota_res_old_compare[k] = v[0]
                    for k, v in quota_res_new_dict.items():
                        quota_res_new_compare[k] = v[0]
                    
                    if (quota_new != quota_old) or (quota_res_old_compare != quota_res_new_compare):
                        # Prepare change announcement embed: course name, section name
                        embed_quota_change = discord.Embed(
                            title=f"{value.get('title', 'Error')}: {key2}",
                            color=0xeed49f  # Yellow
                        )
                        # Prepare header of change announcement
                        embed_quota_change.set_author(name="🍋 Quota changed!")

                        # Display (total) quota change
                        changed_section_quotas = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
                        changed_section_quotas += f"{trim_section(key2):<8}| "
                        for i in range(4, 8):
                            changed_section_quotas += '{:<6}'.format(value2[i].split("\n", 1)[0])

                        # Add field (Total quotas)
                        if int(quota_new) > int(quota_old):
                            total_quota_change_name = f"🍋 Total: {quota_old} -> {quota_new} (+{int(quota_new) - int(quota_old)})"
                        elif int(quota_new) < int(quota_old):
                            total_quota_change_name = f"🍋 Total: {quota_old} -> {quota_new} ({int(quota_new) - int(quota_old)})"
                        else:
                            total_quota_change_name = f"🍋 Total: {quota_new}"

                        # Display (reserved) quota change (adds and changes)
                        for k, v in quota_res_new_dict.items():
                            changed_section_quotas += f"\n{'> Res.':<8}| "
                            # Quota/enrol/avail
                            for i in range(3):
                                changed_section_quotas += f"{v[i]:<6}"
                            # Dept
                            changed_section_quotas += f"For: {k}"

                            # Add field (reserved quotas)
                            # New reserved quota
                            if k not in quota_res_old_dict:
                                total_quota_change_name += f"\n➡️ Reserved ({k}): {v[0]} (New)"
                            # Changed reserved quota
                            elif int(v[0]) != int(quota_res_old_dict[k][0]): 
                                # Determine sign of quota change
                                if int(v[0]) >= int(quota_res_old_dict[k][0]):
                                    res_change_sign = "+"
                                else:
                                    res_change_sign = "-"
                                # Find magnitude of quota change
                                res_change = abs(int(v[0]) - int(quota_res_old_dict[k][0]))

                                total_quota_change_name += f"\n↔️ Reserved ({k}): {quota_res_old_dict[k][0]} -> {v[0]} ({res_change_sign}{res_change})"
                        
                        changed_section_quotas += "\n```"
                        
                        embed_quota_change.add_field(
                            name=total_quota_change_name,
                            value=changed_section_quotas,
                            inline=False
                        )
                        
                        # Display (reserved) quota change (removals)
                        for k, v in quota_res_old_dict.items():
                            if k not in quota_res_new_dict:
                                res_field = f"```\n{'> Res.':<8}| "
                                # Quota/enrol/avail
                                for i in range(3):
                                    res_field += f"{v[i]:<6}"
                                # Dept
                                res_field += f"For: {k}"
                                res_field += "\n```"
                            
                                # Add field
                                embed_quota_change.add_field(
                                    name=f"⬅️ Reserved ({k}): {v[0]} (Removed)",
                                    value=res_field,
                                    inline=False
                                )

                        # Send the announcement
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_quota_change)
                        await send_to_subscribers(bot, key, embed_quota_change)
                        changed = True
                    
                    # 🥭 Date & Time changed!
                    # Initialize list of values
                    # Time list elements are guaranteed to be unique
                    time_list_new = value2[1].split("\n\n\n")
                    time_list_old = old_quotas[key]['sections'][key2][1].split("\n\n\n")

                    # Prepare change announcement text: course name, section name, section ID
                    embed_time_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xee99a0  # Maroon
                    )
                    # Prepare header of change announcement
                    embed_time_change.set_author(name="🥭 Date & Time changed!")

                    # Check additions and removals
                    time_deltas = list_diffs(time_list_new, time_list_old)
                    time_diffed = diff_highlight(time_list_new, time_list_old)

                    # Add old date & time field
                    time_old_field = "```diff\n"  # Diff syntax highlighting
                    time_old_field += "\n\n".join(time_diffed[1])
                    time_old_field += "\n```"
                    # Add field to embed
                    embed_time_change.add_field(
                        name="🥭 Old",
                        value=time_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new date & time field
                    time_new_field = "```diff\n"  # Diff syntax highlighting
                    time_new_field += "\n\n".join(time_diffed[0])
                    time_new_field += "\n```"
                    # Add field to embed
                    embed_time_change.add_field(
                        name="🥭 New",
                        value=time_new_field,
                        inline=True  # Split view comparison
                    )

                    # Display number of changes
                    embed_time_change.set_footer(text=f"🥭 {len(time_deltas[0])} additions, {len(time_deltas[1])} removals")

                    # If there is time change, send the announcement
                    if time_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_time_change)
                        await send_to_subscribers(bot, key, embed_time_change)
                        changed = True

                    # 🥝 Venue changed!
                    # Initialize list of values
                    venue_list_new = value2[2].split("\n")
                    venue_list_old = old_quotas[key]['sections'][key2][2].split("\n")
                    # Remove empty list elements
                    venue_list_new = [venue for venue in venue_list_new if venue != ""]
                    venue_list_old = [venue for venue in venue_list_old if venue != ""]
                    # Remove duplicates
                    # Create a dict using the list items as keys to automatically remove any duplicates because dicts cannot have duplicate keys
                    # Convert dict back into a list, assign it to the list of venues
                    venue_list_new = list(dict.fromkeys(venue_list_new))
                    venue_list_old = list(dict.fromkeys(venue_list_old))

                    # Prepare change announcement text: Header, course name, section name, section ID
                    embed_venue_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xa6da95  # Green
                    )
                    # Prepare header of change announcement
                    embed_venue_change.set_author(name="🥝 Venue changed!")

                    # Check additions and removals
                    venue_deltas = list_diffs(venue_list_new, venue_list_old)
                    venue_diffed = diff_highlight(venue_list_new, venue_list_old)

                    # Add old venue field
                    venue_old_field = "```diff\n"  # Diff syntax highlighting
                    venue_old_field += "\n".join(venue_diffed[1])
                    venue_old_field += "\n```"
                    # Add field to embed
                    embed_venue_change.add_field(
                        name="🥝 Old",
                        value=venue_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new venue field
                    venue_new_field = "```diff\n"  # Diff syntax highlighting
                    venue_new_field += "\n".join(venue_diffed[0])
                    venue_new_field += "\n```"
                    # Add field to embed
                    embed_venue_change.add_field(
                        name="🥝 New",
                        value=venue_new_field,
                        inline=True  # Split view comparison
                    )
                    
                    # Display number of changes
                    embed_venue_change.set_footer(text=f"🥝 {len(venue_deltas[0])} additions, {len(venue_deltas[1])} removals")

                    # If there is venue change, send the announcement
                    if venue_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_venue_change)
                        await send_to_subscribers(bot, key, embed_venue_change)
                        changed = True
                    
                    # 🍇 Instructor changed!
                    # Initialize list of values
                    inst_list_new = value2[3].split("\n")
                    inst_list_old = old_quotas[key]['sections'][key2][3].split("\n")
                    # Remove empty list elements
                    inst_list_new = [inst for inst in inst_list_new if inst != ""]
                    inst_list_old = [inst for inst in inst_list_old if inst != ""]
                    # Remove duplicates
                    # Create a dict using the list items as keys to automatically remove any duplicates because dicts cannot have duplicate keys
                    # Convert dict back into a list, assign it to the list of instructors
                    inst_list_new = list(dict.fromkeys(inst_list_new))
                    inst_list_old = list(dict.fromkeys(inst_list_old))

                    # Prepare change announcement text: Header, course name, section name, section ID
                    embed_inst_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xc6a0f6  # Mauve
                    )
                    # Prepare header of change announcement
                    embed_inst_change.set_author(name="🍇 Instructor changed!")

                    # Check additions and removals
                    inst_deltas = list_diffs(inst_list_new, inst_list_old)
                    inst_diffed = diff_highlight(inst_list_new, inst_list_old)

                    # Add old instructor field
                    inst_old_field = "```diff\n"  # Diff syntax highlighting
                    inst_old_field += "\n".join(inst_diffed[1])
                    inst_old_field += "\n```"
                    # Add field to embed
                    embed_inst_change.add_field(
                        name="🍇 Old",
                        value=inst_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new instructor field
                    inst_new_field = "```diff\n"  # Diff syntax highlighting
                    inst_new_field += "\n".join(inst_diffed[0])
                    inst_new_field += "\n```"
                    # Add field to embed
                    embed_inst_change.add_field(
                        name="🍇 New",
                        value=inst_new_field,
                        inline=True  # Split view comparison
                    )
                    
                    # Display number of changes
                    embed_inst_change.set_footer(text=f"🍇 {len(inst_deltas[0])} additions, {len(inst_deltas[1])} removals")

                    # If there is instructor change, send the announcement
                    if inst_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_inst_change)
                        await send_to_subscribers(bot, key, embed_inst_change)
                        changed = True
                    
                    # 🫐 Remarks changed!
                    # Initialize list of values
                    remarks_list_new = value2[8].split("\n")
                    remarks_list_old = old_quotas[key]['sections'][key2][8].split("\n")
                    # Remove empty list elements, including special space characters
                    # Remove "> " from the beginning of line too
                    remarks_list_new = [r.strip("> ") for r in remarks_list_new if r not in ['', '\xa0', '\u00a0']]
                    remarks_list_old = [r.strip("> ") for r in remarks_list_old if r not in ['', '\xa0', '\u00a0']]

                    # Prepare change announcement text: Header, course name, section name, section ID
                    embed_remarks_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0x8aadf4  # Blue
                    )
                    # Prepare header of change announcement
                    embed_remarks_change.set_author(name="🫐 Remarks changed!")

                    # Check additions and removals
                    remarks_deltas = list_diffs(remarks_list_new, remarks_list_old)
                    remarks_diffed = diff_highlight(remarks_list_new, remarks_list_old)

                    # Add old remarks field
                    remarks_old_field = "```\n"  # Field text becomes "diff" if there is no content
                    if remarks_diffed[1] != []:
                        remarks_old_field = "```diff\n"  # Diff syntax highlighting
                    remarks_old_field += "\n".join(remarks_diffed[1])
                    remarks_old_field += "\n```"
                    # Add field to embed
                    embed_remarks_change.add_field(
                        name="🫐 Old",
                        value=remarks_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new remarks field
                    remarks_new_field = "```\n"  # Field text becomes "diff" if there is no content
                    if remarks_diffed[0] != []:
                        remarks_new_field = "```diff\n"  # Diff syntax highlighting
                    remarks_new_field += "\n".join(remarks_diffed[0])
                    remarks_new_field += "\n```"
                    # Add field to embed
                    embed_remarks_change.add_field(
                        name="🫐 New",
                        value=remarks_new_field,
                        inline=True  # Split view comparison
                    )

                    # Display number of changes
                    embed_remarks_change.set_footer(text=f"🫐 {len(remarks_deltas[0])} additions, {len(remarks_deltas[1])} removals")

                    # If there is remarks change, send the announcement
                    if remarks_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_remarks_change)
                        await send_to_subscribers(bot, key, embed_remarks_change)
                        changed = True

    for key3, value3 in old_quotas.items():
        # Skip "time" entry
        if key3 == "time":
            continue
        # ☕ Course deleted!
        if key3 not in new_quotas:
            # await channels.get(key3[0: 4], channels['other']).send(f"☕ **Course deleted!**\n{value3.get('title', 'Error')}\n{len(value3['sections'])} sections")
            # Prepare change announcement embed: course name
            embed_delete_course = discord.Embed(
                title=f"{value3.get('title', 'Error')}",
                color=0xf4dbd6  # Rosewater
            )
            # Prepare header of change announcement
            embed_delete_course.set_author(name="☕ Course deleted!")

            # Display list of sections
            delete_course_sections = "```\n"
            delete_course_sections += "\n".join(list(value3['sections'].keys()))
            delete_course_sections += "\n```"

            # Add field
            embed_delete_course.add_field(
                name=f"☕ {len(value3['sections'])} sections",
                value=delete_course_sections,
                inline=False
            )

            # Send the announcement
            await channels.get(key3[0: 4], channels['other']).send(embed=embed_delete_course)
            await send_to_subscribers(bot, key3, embed_delete_course)
            changed = True

        else:
            for key4, value4 in value3['sections'].items():
                # 🍹 Section deleted!
                if key4 not in new_quotas[key3]['sections']:
                    # await channels.get(key3[0: 4], channels['other']).send(f"🍹 **Section deleted!**\n{value3.get('title', 'Error')}: {key4}")
                    # Prepare change announcement embed: course name, section name
                    embed_delete_section = discord.Embed(
                        title=f"{value3.get('title', 'Error')}: {key4}",
                        color=0xf5a97f  # Peach
                    )
                    # Prepare header of change announcement
                    embed_delete_section.set_author(name="🍹 Section deleted!")

                    # Display quota of section: total
                    delete_section_quotas = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
                    delete_section_quotas += f"{trim_section(key4):<8}| "
                    for i in range(4, 8):
                        delete_section_quotas += '{:<6}'.format(value4[i].split("\n", 1)[0])
                    
                    # Display quota of section: reserved
                    quota_delete = value4[4].split("\n")
                    delete_res_dict = {}
                    if len(quota_delete) >= 3:
                        # Dict to store dept names and numbers
                        for i in range(2, len(quota_delete)):
                            # Split dept name from numbers
                            quota_delete_res = quota_delete[i].split(": ")
                            delete_res_dict[quota_delete_res[0]] = quota_delete_res[1].split("/")
                    
                    for k, v in delete_res_dict.items():
                        delete_section_quotas += f"\n{'> Res.':<8}| "
                        # Quota/enrol/avail
                        for i in range(3):
                            delete_section_quotas += f"{v[i]:<6}"
                        # Dept
                        delete_section_quotas += f"For: {k}"

                    delete_section_quotas += "\n```"
                    
                    # Add field
                    embed_delete_section.add_field(
                        name="🍹 Quota",
                        value=delete_section_quotas,
                        inline=False
                    )
                    
                    # Send the announcement
                    await channels.get(key3[0: 4], channels['other']).send(embed=embed_delete_section)
                    await send_to_subscribers(bot, key3, embed_delete_section)
                    changed = True

    return changed

async def download_quotas(bot, current_loop):
    url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/"
    
    try:
        page = requests.get(url)

        soup = bs4.BeautifulSoup(page.content, "html.parser")
    
        letters = soup.select('.depts')[0]
    except Exception as error:  # Failed to connect to server!
        # Print exception to console
        traceback.print_exc()

        # Send exception to errors channel
        await send_loop_exception(current_loop, "Failed to connect to server!", error)

        return update_time()

    quotas = {}

    for letter in letters:
        sub_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/subject/{letter.get_text()}"

        try:
            sub_page = requests.get(sub_url, timeout=10)
        except Exception as e:  # Timed out!
            # Print exception to console
            traceback.print_exc()

            # Send exception to errors channel
            send_loop_exception(current_loop, "Timed out!", e)
            
            return update_time()

        sub_soup = bs4.BeautifulSoup(sub_page.content, "html.parser")

        classes = sub_soup.select('#classes > .course')

        for course in classes:
            try:
                course_dict = {}

                course_title = course.find("h2").get_text()
            
                course_code = course.select(".courseanchor > a")[0]["name"]
            except:
                continue
            
            # No more course info im lazy
            # Course info start
            course_info = course.select(".courseinfo > .courseattr.popup > .popupdetail > table")[0]
            course_info_rows = course_info.select('tr')

            info_dict = {}

            # Special course info: matching
            matching_info = course.find("div", {"class": "matching"})
            if matching_info is not None:
                matching_info = matching_info.get_text()
                info_dict["MATCHING"] = matching_info

            for row in course_info_rows:
                try:
                    heading = row.find('th')
                    heading = heading.get_text("\n")

                    data = row.select('td')[0]
                    data = data.get_text("\n")

                    info_dict[heading] = data
                except:
                    continue
            # Course info end
            
            section_dict = {}
            course_sections = course.select(".sections")[0]
            course_sections = course_sections.find_all("tr", ["newsect secteven", "newsect sectodd", "secteven", "sectodd"])

            for idx, section in enumerate(course_sections):
                # Append extra section times/instructor information to section entry (1/2)
                if section['class'][0] in ["secteven", "sectodd"]:
                    continue

                section_data = section.select("td")
                section_cols = []
                for col in section_data:
                    section_cols.append(col.get_text("\n"))
                
                # Append extra section times/instructor information to section entry (2/2)
                # try:
                #     next_section = course_sections[idx + 1]
                #     if next_section['class'] in ["secteven", "sectodd"]:
                #         extra_data = next_section.select("td")

                #         for idx2, datum in enumerate(extra_data):
                #             section_cols[idx2 + 1] += f"\n{datum}"
                # except IndexError:
                #     pass
                    
                section_dict[section_cols[0]] = section_cols

                try:
                    next = 1
                    while course_sections[idx + next]['class'][0] in ["secteven", "sectodd"]:
                        next_section = course_sections[idx + next]
                        if next_section['class'][0] in ["secteven", "sectodd"]:
                            extra_data = next_section.select("td")

                            for idx2, datum in enumerate(extra_data):
                                section_dict[section_cols[0]][idx2 + 1] += "\n\n\n" + datum.get_text("\n")
                        
                        next += 1
                except IndexError:
                    pass
            
            # Add data to dictionary for course
            course_dict['title'] = course_title
            course_dict['sections'] = section_dict
            course_dict['info'] = info_dict

            quotas[course_code] = course_dict
    
    quotas['time'] = update_time()
    
    # Move quotas of last minute to another file if quotas changed
    # oldfile = open('quotas_old.json', 'w', encoding='utf-8')
    # old_quotas = open_quotas()
    # if check_quotas_validity():
    #     json.dump(old_quotas, oldfile, indent = 4)
    # # Make old quotas file empty if quota file is corrupted
    # else:
    #     json.dump({}, oldfile, indent = 4)
    if current_loop == 0:
        oldfile = open('quotas_old.json', 'w', encoding='utf-8')
        try:
            json.dump(quotas, oldfile, indent=4)
        except:
            json.dump({}, oldfile, indent=4)
    elif await check_diffs(bot=bot, new_quotas=quotas, old_quotas=open_old_quotas()):
        oldfile = open('quotas_old.json', 'w', encoding='utf-8')
        try:
            json.dump(quotas, oldfile, indent=4)
        except:
            json.dump({}, oldfile, indent=4)

    # Save quotas to json file
    outfile = open('quotas.json', 'w', encoding='utf-8')
    try:
        json.dump(quotas, outfile, indent = 4)
    except:
        json.dump({}, outfile, indent=4)

    return update_time() 
