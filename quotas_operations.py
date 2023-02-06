# quotas_operations.py
import discord

import os
import json
import re

import config

# Change working directory to wherever this is in
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def open_quotas():
    quotas = open('quotas.json', encoding='utf-8')
    quotas = json.load(quotas)
    return quotas

def trim_section(section_code):
    section_trim = re.findall("[A-Z]+[0-9]+", section_code)[0]
    return section_trim

def compose_message(course_code):
    quotas = open_quotas()

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
        color=config.color_info)
    
    quota_field = f"```\n{'Section':<12}{'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
    for key, value in course_dict['sections'].items():
        quota_field += f"{trim_section(key):<12}"
        for i in range(4, 8):
            quota_field += f"{value[i]:<6}"
        quota_field += "\n"
    quota_field += "```"

    embed_quota.add_field(name="🌸 Sections", value=quota_field, inline=False)

    # Add warning message
    embed_quota.add_field(name="🌸 Tab may become unresponsive while updating quotas!",
        value="If your command failed, try again after a few seconds!")

    embed_quota.set_footer(text=f"🕒 Last updated:\n{quotas['time']}")

    return embed_quota