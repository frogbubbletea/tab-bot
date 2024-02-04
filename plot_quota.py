import pymongo
import discord

import io
import base64
import datetime
from zoneinfo import ZoneInfo

import mplcatppuccin
from mplcatppuccin.palette import load_color
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

import config
import get_quota

# Configure plot theme
plt.style.use(["ggplot", "latte"])

# Load line colors
quota_line_color = load_color("latte", "yellow")
quota_bg_color = load_color("macchiato", "yellow")  # Uncovered area is equal to enrolled
enrol_line_color = load_color("latte", "yellow")
enrol_bg_color = load_color("macchiato", "yellow")
avail_line_color = load_color("latte", "sky")
avail_bg_color = load_color("macchiato", "sky")
waitlist_line_color = load_color("latte", "red")
waitlist_bg_color = load_color("macchiato", "red")
axis_line_color = load_color("latte", "text")

# Configure plot font
plt.rcParams["font.family"] = "Inter"

def compose_plot(course_code: str, section: str, page=0):
    # TODO: Plot the section statistics
    # Displaying placeholder plot for now
    # fig, ax = plt.subplots()
    # ax.plot([0, 1, 2, 3], [1, 2, 3, 4])
    # return fig

    # Find all snapshots of specified section
    course_col = get_quota.trend_db[course_code]
    section_query = { "section_code": section }
    section_snapshots = list(course_col.find(section_query, sort=[('time', 1)]))

    # Add intermediate data points at 1 interval before recorded change if needed
    for i in range(1, len(section_snapshots)):
        if section_snapshots[i]["loop"] - section_snapshots[i - 1]["loop"] > 1:
            section_snapshots.insert(
                i,
                {
                    "section_code": section,
                    "time": section_snapshots[i]["time"] - get_quota.trend_snapshot_interval,
                    "loop": section_snapshots[i]["loop"] - 1,
                    "total": section_snapshots[i - 1]["total"],  # Should have the same quotas as the last snapshot before recorded change
                    "reserved": section_snapshots[i - 1]["reserved"]
                }
            )
    
    # Set latest data point at last update time if no change recorded at that time
    if section_snapshots[-1]["loop"] < get_quota.get_trend_update_time(True):
        section_snapshots.append(
            {
                "section_code": section,
                "time": get_quota.get_trend_update_time(),
                "loop": get_quota.get_trend_update_time(True),
                "total": section_snapshots[-1]["total"],  # Should have the same quotas as the last snapshot before recorded change
                "reserved": section_snapshots[-1]["reserved"]
            }
        )
    
    # Format data into lines
    time_xpoints = np.array([get_quota.time_from_stamp(d.get('time', 0)) for d in section_snapshots])
    total_quota_ypoints = np.array([d.get('total', [0, 0, 0, 0])[0] for d in section_snapshots])
    total_enrol_ypoints = np.array([d.get('total', [0, 0, 0, 0])[1] for d in section_snapshots])
    total_avail_ypoints = np.array([d.get('total', [0, 0, 0, 0])[2] for d in section_snapshots])
    total_wait_ypoints = np.array([0 - d.get('total', [0, 0, 0, 0])[3] for d in section_snapshots])  # Display waitlist in negative Y axis
    total_wait_ypoints_ma = np.ma.masked_where(total_wait_ypoints >= 0, total_wait_ypoints)  # Don't display waitlist line when waitlist is 0

    fig, ax = plt.subplots()

    # Set axes limits
    ax.set_xlim([time_xpoints.min(), time_xpoints.max()])
    ylim_value = np.array([total_quota_ypoints.max(), abs(total_wait_ypoints.min())]).max()  # Determine largest magnitude on the graph
    ax.set_ylim([0 - ylim_value - 10, ylim_value + 10])

    # Set x-axis label to date and time (Timezone of HKUST)
    # https://stackoverflow.com/questions/70805592/pyplot-positive-values-on-y-axis-in-both-directions
    axis_timeformat = mdates.DateFormatter('%m/%d %H:%M', tz=get_quota.hkust_time_zone)
    ax.xaxis.set_major_formatter(axis_timeformat)

    # Set y-axis label to absolute value
    # https://stackoverflow.com/questions/70805592/pyplot-positive-values-on-y-axis-in-both-directions
    ax.yaxis.set_major_formatter(lambda x, pos: f'{abs(x):g}')

    # Plot the graph
    ax.plot(time_xpoints, total_quota_ypoints, color=quota_line_color, label="Quota")
    ax.fill_between(time_xpoints, total_quota_ypoints, color=quota_bg_color)

    # ax.plot(time_xpoints, total_enrol_ypoints, color=enrol_line_color)
    # ax.fill_between(time_xpoints, total_enrol_ypoints, color=enrol_bg_color, alpha=0.3)

    ax.plot(time_xpoints, total_avail_ypoints, color=avail_line_color, label="Avail")
    ax.fill_between(time_xpoints, total_avail_ypoints, color=avail_bg_color)

    ax.plot(time_xpoints, total_wait_ypoints_ma, color=waitlist_line_color, label="Wait")
    ax.fill_between(time_xpoints, total_wait_ypoints_ma, color=waitlist_bg_color)

    # Highlight the x-axis
    ax.plot(time_xpoints, np.zeros_like(time_xpoints), color=axis_line_color)

    # Rotate x-axis labels for date and time display
    fig.autofmt_xdate()

    # Add legend
    ax.legend()

    # Set axes labels and title
    ax.set_xlabel("Time")
    ax.set_ylabel("No. of people")
    total_title = f"{course_code[0: 4] + ' ' + course_code[4: ]} {section}: Total"
    ax.set_title(total_title)

    # Finish
    return fig

def compose_embed_with_plot(course_code: str, section: str, page=0):
    # Placeholder course code and section code
    # course_title = "COMP 4521 - Mobile Application Development (3 units)"
    # section_name = "L1 (2131)"

    quotas = get_quota.open_quotas()

    # Check if quotas file is available
    if not get_quota.check_quotas_validity():
        return "unavailable", None
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "course_code", None
    else:
        if course_code == "time":
            return "course_code", None
    # Get the course title from the course code
    course_title = course_dict.get("title", "Error")
    
    # Check if section code is valid
    # Get list of (trimmed) section codes to compare against input
    section_codes = list(map(get_quota.trim_section, course_dict["sections"].keys()))
    try:
        section_idx = section_codes.index(section)
    except ValueError:
        return "section_code", None
    # Get the full section code from the input
    section_name = list(course_dict["sections"].keys())[section_idx]

    # Compose embed containing the plot
    embed_plot = discord.Embed(
        title=f"{course_title}: {section_name}",
        color=config.color_success,
        timestamp=get_quota.time_from_stamp(get_quota.get_trend_update_time())
    )

    # Set heading and footer
    embed_plot.set_author(name="🍊 Enrollment graph of")
    embed_plot.set_footer(text="🕒 Last updated")

    # Plot the section's statistics
    section_plot_fig = compose_plot(course_code, section)
    section_plot_stringIObytes = io.BytesIO()

    # Export image of plot to discord
    section_plot_fig.savefig(section_plot_stringIObytes, format='png')
    section_plot_stringIObytes.seek(0)
    section_plot_png_data = base64.b64encode(section_plot_stringIObytes.read()).decode()
    section_plot_image_file = discord.File(io.BytesIO(base64.b64decode(section_plot_png_data)), filename="section_plot.png")
    embed_plot.set_image(url="attachment://section_plot.png")

    return embed_plot, section_plot_image_file
    