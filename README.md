# 🍄 tab-bot

Two Discord bots that does helpful stuff with course quotas in HKUST! 🐈‍⬛

https://discord.gg/RNmMMF6xHY


## 🥁 Tab
Tab searches the servers of UST to get course data and look for quota changes!

- Tab [se](https://youtu.be/FXsGCieXm1E)nds notifications to a Discord server when changes are recorded!
- It updates every 1.5 minutes to catch changes as quickly as possible!

## 🍦 Hill
Hill uses data collected by Tab to provide course info on demand! Using its slash commands, you can check:

- Quotas
- Sections (schedules, venues, instructors)
- General information (pre-reqs, exclusions, descriptions)

of a course!

Hill can also be added to other servers!

---

## 🖼️ Screenshots
|||
| :---         | :---    |
| Tab: a new course is added | ![Tab sends a message when a new course is added](sample_screenshots/tab/tab_02_hill_08/new_course.png) |
| Tab: a new section (of an existing course) is added | ![Tab sends a message when a new section (of an existing course) is added](sample_screenshots/tab/tab_02_hill_08/new_section.png) |
| Tab: the quota of a section is changed | ![Tab sends a message when the quota of a section is changed](sample_screenshots/tab/tab_02_hill_08/quota_changed.png) |
| Tab: a course is deleted | ![Tab sends a message when a course is deleted](sample_screenshots/tab/tab_02_hill_08/course_deleted.png) |
| Tab: a section (of a course) is deleted | ![Tab sends a message when a section (of a course) is deleted](sample_screenshots/tab/tab_02_hill_08/section_deleted.png) |
| Using Hill's command: `/info` | ![Using Hill's command: `/info`](sample_screenshots/hill/0-8/hill_08_info.png) |
| Using Hill's command: `/sections` | ![Using Hill's command: `/sections`](sample_screenshots/hill/0-8/hill_08_sections.png) |
| Using Hill's command: `/quota` | ![Using Hill's command: `/quota`](sample_screenshots/hill/0-8/hill_08_quota.png) |
| Hill: command autocompletion | ![Hill: command autocompletion](sample_screenshots/hill/0-8/hill_08_autocomplete.png) |
---

## 🌟 Credits
Tab and Hill are made possible by the following projects:
- [evnchn/Course-Quota-Online](https://github.com/evnchn/Course-Quota-Online): Uses the same technologies as this project!
- [henveloper/discord-ustquotatracker](https://github.com/henveloper/discord-ustquotatracker): The original UST course quota tool!
- [HKUST Class Schedule & Quota](https://w5.ab.ust.hk/wcq/cgi-bin/): The *original* original course quota website from UST!