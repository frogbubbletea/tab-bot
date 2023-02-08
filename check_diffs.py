# diffs.py
import os
import json

import discord

from quotas_operations import open_quotas, check_quotas_validity
from bot import channels

# Change working directory to wherever this is in
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def check_diffs():
    # Open quotas files
    new_quotas = open_quotas()
    old_quotas = open('quotas_old.json', encoding='utf-8')
    old_quotas = json.load(old_quotas)

    # No comparison if current quotas file or last quotas file is corrupted
    if (not check_quotas_validity) or (old_quotas == {}):
        return
    
    for key, value in new_quotas.items():
        # New course
        if key not in old_quotas:
            channels.get(key[0: 4], channels['other']).send(f"🥑 New course!\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
            # DEBUG PRINT
            print(f"🥑 New course!\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
        else:
            for key2, value2 in value['sections'].items():
                # New section
                if key2 not in old_quotas[key]['sections']:
                    channels.get(key[0: 4], channels['other']).send(f"🍅 New section!\n{value.get('title', 'Error')} {key2}\nQuota {value2[4]}")
                    # DEBUG PRINT
                    print(f"🍅 New section!\n{value.get('title', 'Error')} {key2}\nQuota {value2[4]}")
                # Quota change
                elif value2[4] != value['sections'][key2][4]:
                    channels.get(key[0: 4], channels['other']).send(f"🍋 Quota changed!\n{value.get('title', 'Error')} {key2}\n{value['sections'][key2][4]}")
                    # DEBUG PRINT
                    print(f"🍋 Quota changed!\n{value.get('title', 'Error')} {key2}\n{value['sections'][key2][4]}")
    