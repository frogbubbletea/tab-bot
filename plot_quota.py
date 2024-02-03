import pymongo
import discord

import io
import base64
import datetime

import mplcatppuccin
import matplotlib.pyplot as plt
import numpy as np

import config

# Configure plot theme
plt.style.use(["ggplot", "macchiato"])

def compose_plot(course_code: str, section: str):
    # TODO: Plot the section statistics
    # Displaying placeholder plot for now
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3], [1, 2, 3, 4])
    return fig

def compose_embed_with_plot(course_code: str, section: str):
    # TODO: Get actual course title and section name
    # Placeholder course code and section code
    course_title = "COMP 4521 - Mobile Application Development (3 units)"
    section_name = "L1 (2131)"

    # Compose embed containing the plot
    embed_plot = discord.Embed(
        title=f"{course_title}: {section_name}",
        color=config.color_success,
        timestamp=datetime.datetime.now()  # TODO: statistics update time
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
    