import os  # environ
import datetime
from apiclient import discovery

# TODO: make environment variables?
API_KEY = "AIzaSyBTn4GzVTJ4bG_zR9IF0ijd4Y5LbdwDKnk"
CALENDAR_ID = "metropolitanweightlifting@gmail.com"


def get_latest(amount):
    service = discovery.build("calendar", "v3", developerKey=API_KEY)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=amount,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return result.get('items', [])
