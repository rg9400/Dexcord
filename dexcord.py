#!/usr/bin/env python
import requests
import os
import sys
import json
import sqlite3
import datetime
import time

################################ CONFIG BELOW ################################
WEBHOOK_URL = 'YOURDISCORDWEBHOOKHERE'
###############################################################################

## CODE BELOW ##

def check_if_values_match(db_file, table_name, id, timestamp):
    """
    Checks if the values in a dictionary match the corresponding rows in a database table.

    Args:
        db_file (str): Path to the SQLite database file.
        table_name (str): Name of the table in the database.
        dictionary (dict): Dictionary containing the key-value pairs to check.
    """

    con = sqlite3.connect(db_file)
    cursor = con.cursor()
    
    query = f"SELECT * FROM {table_name} WHERE id = ?"
    cursor.execute(query, (id,))
    result = cursor.fetchone()

    if not result:
        print(f"Need to process item {id}")
        con.close()
        return False

    if result and timestamp not in result:
        print(f"Need to update item {id} for timestamp {timestamp}")
        con.close()
        return False

    con.close()
    return True

def main():
    #Check if database and table exist, else create them
    db_file = os.path.join(os.path.dirname(sys.argv[0]), 'dexcord.db')
    table_name = 'updates'
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    try:
        cur.execute("SELECT * FROM {}".format(table_name))
    except sqlite3.OperationalError:
        print("Need to create updates table")
        if sqlite3.OperationalError:
            try:
                cur.execute("CREATE TABLE updates(id type UNIQUE, updated_at)")
            except sqlite3.Error() as e:
                print(e, " occured")
    con.commit()
    con.close()

    #SeaDex URL with latest updates to best releases
    url = 'https://releases.moe/api/collections/torrents/records?sort=-updated&filter=(isBest=true)'

    # Fetch JSON data from the URL
    response = requests.get(url)
    data = response.json().get('items', [])

    for item in data:
        id = item['id']
        timestamp = item['updated']
        if not check_if_values_match(db_file, table_name, id, timestamp):
            dualAudio = str(item.get('dualAudio', 'No Dual Audio info'))
            releaseGroup = item.get('releaseGroup', 'No Release Group info available')
            tracker = item.get('tracker', 'No tracker available')
            url = item.get('url', 'No URL available')
            created = item.get('created', 'Creation timestamp not available')
            title = next(iter(item['files']), 'No Files').get('name', 'No File Name')
            files = item.get('files', [])
            file_names = "\n".join([file.get('name', 'Unnamed file') for file in files]) if files else "No files available"
            #Truncate file list to 1024 characters due to Discord limit
	    file_list = file_names[:1018] if len(file_names) > 1018 else file_names
	    if tracker == "Nyaa":
                thumbnail = "https://raw.githubusercontent.com/rg9400/Dexcord/refs/heads/main/nyaa.png"
            elif tracker == "AB":
                thumbnail = "https://raw.githubusercontent.com/rg9400/Dexcord/refs/heads/main/animebytes.jpg"
		url = f"https://animebytes.tv{url}"
            else:
                thumbnail = "https://raw.githubusercontent.com/rg9400/Dexcord/refs/heads/main/seadex.png"

            # Create the embed
            embed = [{
                "color": 16744448,
                "title": title,
                "url": url,
                "author": {
                    "name": "Dexcord",
                    "icon_url": "https://raw.githubusercontent.com/rg9400/Dexcord/refs/heads/main/seadex.png",
                    "url": "https://releases.moe/"
                },
                "thumbnail": {
		            "url": thumbnail
	            },
                "fields": [
                    {
                        "name": "Release Group",
                        "value": releaseGroup,
                        "inline": True
                    },
                    {
                        "name": "Dual Audio",
                        "value": dualAudio,
                        "inline": True
                    },
                    {
                        "name": "Tracker",
                        "value": tracker,
                        "inline": True
                    },
                    {
                        "name": "Created",
                        "value": created,
                        "inline": True
                    },
                    {
                        "name": "Files",
                        "value": f"```{file_list}```",
                        "inline": False
                    }
                ],
                "timestamp": timestamp,
                "footer": {
                    "text": "Dexcord"
                }
            }]

            #Construct the Discord payload
            payload = {
                "embeds": embed
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Sending the post request to Discord webhook
            response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)

            if response.status_code == 204:
                print(f"Update for {id} posted on Discord")
                con = sqlite3.connect(db_file)
                cur = con.cursor()
                insert = (id, timestamp)
                cur.execute("""
                    INSERT INTO updates VALUES
                        {}
				ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at
                """.format(insert))
                con.commit()
                con.close()
            else:
                print(f"Failed to send to Discord. Status code: {response.status_code}")

            time.sleep(2)

main()
