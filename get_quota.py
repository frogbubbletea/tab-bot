# get_quota.py
import requests
import bs4

import discord

import os
import json
from datetime import datetime
import re

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
semester_code = 2230

def trim_section(section_code):
    section_trim = re.findall("[A-Z]+[0-9]*[A-Z]*", section_code)[0]
    return section_trim

def update_time():
    now = datetime.now()
    date_time = now.strftime("%Y/%m/%d %H:%M:%S")
    return date_time

# Dict containing all subject channels
channels = None
async def get_channels(bot):
    global channels
    channels = await subject_channels.find_channels(bot)

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
    try:
        if 'time' in quotas:
            return True
        else:
            return False
    except TypeError:  # Error raised if quotas file is corrupted
        return False

# Compose message of course quotas for "quota" command
def compose_message(course_code):
    quotas = open_quotas()

    # Check if quotas file is available
    if (quotas == False) or (not check_quotas_validity()):
        embed_quota_unavailable = discord.Embed(title=f"⚠️ Quotas are unavailable at the moment!",
            description="Try again in a minute.",
            color=config.color_failure)
        return embed_quota_unavailable

    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    # Compose list
    embed_quota = discord.Embed(title=f"🍓 {course_dict['title']}",
        color=config.color_success)
    
    quota_field = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
    for key, value in course_dict['sections'].items():
        quota_field += f"{trim_section(key):<8}| "
        for i in range(4, 8):
            quota_field += '{:<6}'.format(value[i].split("\n", 1)[0])
        quota_field += "\n"
    quota_field += "```"

    embed_quota.add_field(name="🌸 Sections", value=quota_field, inline=False)

    # Add warning message
    embed_quota.add_field(name="🌸 Tab may become unresponsive while updating quotas!",
        value="If your command failed, try again after a few seconds!")

    embed_quota.set_footer(text=f"🕒 Last updated:\n{quotas['time']}")

    return embed_quota

# Helper function to check if course/section/quota changed
async def check_diffs(new_quotas=None, old_quotas=None):
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
        # New course
        if key not in old_quotas:
            await channels.get(key[0: 4], channels['other']).send(f"🥑 **New course!**\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
            changed = True
        else:
            for key2, value2 in value['sections'].items():
                # New section
                if key2 not in old_quotas[key]['sections']:
                    quota_new = value2[4].split("\n", 1)[0]
                    await channels.get(key[0: 4], channels['other']).send(f"🍅 **New section!**\n{value.get('title', 'Error')}: {key2}\nQuota: {quota_new}")
                    changed = True
                # Quota change
                elif value2[4].split("\n", 1)[0] != old_quotas[key]['sections'][key2][4].split("\n", 1)[0]:  
                    quota_old = old_quotas[key]['sections'][key2][4].split("\n", 1)[0]
                    quota_new = value2[4].split("\n", 1)[0]
                    await channels.get(key[0: 4], channels['other']).send(f"🍋 **Quota changed!**\n{value.get('title', 'Error')}: {key2}\n{quota_old} -> {quota_new}")
                    changed = True
    
    for key3, value3 in old_quotas.items():
        # Skip "time" entry
        if key3 == "time":
            continue
        # Deleted course
        if key3 not in new_quotas:
            await channels.get(key3[0: 4], channels['other']).send(f"☕ **Course deleted!**\n{value3.get('title', 'Error')}\n{len(value3['sections'])} sections")
            changed = True
        else:
            for key4, value4 in value3['sections'].items():
                # Deleted section
                if key4 not in new_quotas[key3]['sections']:
                    await channels.get(key3[0: 4], channels['other']).send(f"🍹 **Section deleted!**\n{value3.get('title', 'Error')}: {key4}")
                    changed = True

    return changed

async def download_quotas(current_loop):
    url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/"
    
    try:
        page = requests.get(url)

        soup = bs4.BeautifulSoup(page.content, "html.parser")
    
        letters = soup.select('.depts')[0]
    except:
        return update_time()

    quotas = {}

    for letter in letters:
        sub_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/subject/{letter.get_text()}"

        try:
            sub_page = requests.get(sub_url, timeout=10)
        except:
            print("Timed out!")
            return update_time()

        sub_soup = bs4.BeautifulSoup(sub_page.content, "html.parser")

        classes = sub_soup.select('#classes > .course')

        for course in classes:
            course_dict = {}

            course_title = course.find("h2").get_text()
            
            course_code = course.select(".courseanchor > a")[0]["name"]
            
            # No more course info im lazy
            # course_info = course.select(".courseinfo > .courseattr.popup > .popupdetail > table")[0]
            # course_info_rows = course_info.select('tr')
            # course_headings = []
            # course_datas = []
            # for row in course_info_rows:
            #     heading = row.select('th')[0]
            #     heading = heading.get_text("\n")
            #     print(heading)
            #     course_headings.append(heading)
            #     data = row.select('td')[0]
            #     data = data.get_text("\n")
            #     course_datas.append(data)
            
            section_dict = {}
            course_sections = course.select(".sections")[0]
            course_sections = course_sections.find_all("tr", ["newsect secteven", "newsect sectodd"])

            for section in course_sections:
                section_data = section.select("td")
                section_cols = []
                for col in section_data:
                    section_cols.append(col.get_text("\n"))
                section_dict[section_cols[0]] = section_cols
            
            # Add data to dictionary for course
            course_dict['title'] = course_title
            course_dict['sections'] = section_dict

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
    elif await check_diffs(quotas, open_old_quotas()):
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