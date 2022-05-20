from __future__ import print_function

import datetime
import time
import os.path
import pytz
import textToSpeech as tts

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil.parser import parse as dtparse
from datetime import datetime as dt

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
eventsToday = [] # A list of event objects containing all the events under today
minutesBeforeToAlert = 5
creds = None
service = None
global currentEvent
currentEvent = None


def auth_user():
    global creds
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    print("credentials loaded.")
    

def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

    except HttpError as error:
        print('An error occurred: %s' % error)


def event_is_all_day(e):
    if type(e) != dict:
        raise Exception("Input isn't an event!")
    try:
       dt = e['start'].get('dateTime')
       if dt == None:
           return True
       return False
    except ex:
        print(ex)
        return True
# Returns the next event
def get_next_event():
        ignoreAllDayEvents = True
        # Call the Calendar API
        auth_user()
        service = build('calendar', 'v3', credentials=creds)
        page_token = None
        while True:
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            
            events_result = service.events().list(calendarId='primary', pageToken = page_token, timeMin=now,
                                                  maxResults=1, singleEvents=True,
                                                  orderBy='startTime').execute()
            event = events_result.get('items', [])[0]
            page_token = events_result.get("nextPageToken")

            if (event_is_all_day(event)):
                print("event is all day, let's look for the next event")
            else:
                print("Non-all day event found!")
                break
            if not event:
                print('No upcoming events found.')
                return

        print(type(event))
        return event
        #for event in events:
            #start = event['start'].get('dateTime')
            #print("Datetime of next event: {}".format(start))


def time_to_event(e, minutesBefore = 0):

    dt = dtparse(e['start'].get('dateTime'))
    print("type of dt:")
    print(type(dt))
    if dt == None:
        raise Exception("Non-event passed to time_to_event!")

    now = datetime.datetime.utcnow()
    now = pytz.utc.localize(now)
    diff = (dt - now).total_seconds()
    print("there are " + str(diff) + "seconds to the evnet.")
    return diff

def alert():
    print(f"{currentEvent['summary']} is starting soon!")
    tts.readText(f"Your event {currentEvent['summary']} is starting now!")

def earlyAlert():
    print(f"{currentEvent['summary']} is starting in less than {minutesBeforeToAlert} minutes!")
    tts.readText(f"Hey {user}! Your event, {currentEvent['summary']} is starting in less than {minutesBeforeToAlert} minutes!")

def main_wait_thread():
    global currentEvent
    currentEvent = get_next_event()
    print("current Event: " + str(currentEvent))
    secsToWait = time_to_event(currentEvent)

    if secsToWait < 0:
        # do alarm now
        alert()
    else:
        if (minutesBeforeToAlert > 0):
            print("Wating....")
            time.sleep(secsToWait - 60*minutesBeforeToAlert)
            earlyAlert()
        time.sleep(secsToWait())
        alert()


if __name__ == '__main__':
    main_wait_thread()
