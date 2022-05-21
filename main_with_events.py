from __future__ import print_function

import datetime
import time
import os.path
import pytz
import textToSpeech as tts
import threading
from threading import Event

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil.parser import parse as dtparse
from datetime import datetime as dt

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Settings
CHECK_FOR_CHANGES_TO_CAL_DELAY = 15 # How often to check for changes to the calendar, in seconds
minutesBeforeToAlert = 5 # In minutes, 
user = "Angelina" # The name you would like the "AI" to call you
NOTIFY_WHEN_EVENT_IS_ALMOST_OVER = True # Whether to let the user know when their event is almost over
NOTIFY_WHEN_EVENT_IS_OVER = True # Whether to let the user know when their event ends
DEBUG_MODE = False # If debug mode is false, debug messages won't be printed

secondary_thread = None
eventsToday = [] # A list of event objects containing all the events under today
creds = None
service = None
currentEvent = None
threadEvent = Event()
saySomethingEvent = Event()
whatToSay = ""

def print_debug(s: str):
    if (DEBUG_MODE):
        print(s)

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
        if creds == None:
            print("Loggging the user in...")
            auth_user()
            print("Login sucessful.")
        service = build('calendar', 'v3', credentials=creds)
        page_token = None
        while True:
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            
            events_result = service.events().list(calendarId='primary', timeMin=now, pageToken = page_token,
                                                  maxResults=1, singleEvents=True,
                                                  orderBy='startTime').execute()
            event = events_result.get('items', [])[0]
            page_token = events_result.get("nextPageToken")

            if (event_is_all_day(event) or time_to_event(event) < 0):
                print_debug(f"{event['summary']} is all-day, or already happened.")
            else:
                print_debug(f"{event['summary']} is a non-all day event that hasn't happened yet.")
                return event
            if not event:
                print('No upcoming events found.')
                return


def time_to_event(e, minutesBefore = 0):

    dt = dtparse(e['start'].get('dateTime'))
    if dt == None:
        raise Exception("Non-event passed to time_to_event!")

    now = datetime.datetime.utcnow()
    now = pytz.utc.localize(now)
    diff = (dt - now).total_seconds()
    return diff

def schedule_say(what):
    # schedules the main thread to say something
    global whatToSay
    global saySomethingEvent
    whatToSay = what
    print(whatToSay)
    saySomethingEvent.set()

def alert():
    schedule_say(f"{currentEvent['summary']} is starting now!")

def earlyAlert():
    #print(f"{currentEvent['summary']} is starting in less than {minutesBeforeToAlert} minutes!")
    minutes = int(time_to_event(currentEvent)/60)
    seconds = round(time_to_event(currentEvent) - minutes*60)
    
    if minutes < 1 and seconds < 1:
        alert()
        return
    elif minutes == 0:
        s = f"Hey {user}! Your event, {currentEvent['summary']} is starting in about {seconds} seconds."
    elif seconds == 0:
        s = f"Hey {user}! Your event, {currentEvent['summary']} is starting in about {minutes} minutes."
    else:
        s = f"Hey {user}! Your event, {currentEvent['summary']} is starting in about {minutes} minutes and {seconds} seconds."
    schedule_say(s)

def check_for_changes_to_calendar_thread():
    global currentEvent
    while True:
        if (saySomethingEvent.is_set()):
            print("Speaking...")
            tts.readText(whatToSay)
            saySomethingEvent.clear()
        print_debug("In checking-for-changes thread")
        next_e = get_next_event()
        print_debug(f"New event: {next_e['summary']} Current event: {currentEvent['summary']}")
        if (next_e != currentEvent):
            print("Local calendar synced with Google Calendar.")
            # Tell the other thread it needs to restart
            threadEvent.set()
            currentEvent = get_next_event()
            # Calendar updated
            
        else:
            print_debug("nope, current event is still the same")
        saySomethingEvent.wait(CHECK_FOR_CHANGES_TO_CAL_DELAY)

def main_wait_thread():
    global currentEvent
    print_debug(f"currentEvent " + str(currentEvent))
    while True:
        #tts.readText("testo")
        print_debug("In notification/alarm thread.")
        currentEvent = get_next_event()
        print(f"Upcoming event: {currentEvent['summary']}")
        secsToWait = time_to_event(currentEvent)

        if secsToWait <= 0:
            # do alarm now
            alert()
        else:
            if (secsToWait > minutesBeforeToAlert * 60):
                print("Waiting for alarm to go off....")
                s = threadEvent.wait(secsToWait - 60*minutesBeforeToAlert) # wait for the seconds, unless we are interrupted by the flag being set
                if (s): # if the flag is set, reset the timer based on the new time
                    print_debug("is this being called?")
                    threadEvent.clear()
                    continue
                earlyAlert()
            else:
                #print("made it")
                earlyAlert()
            print("Waiting for alarm to go off....")
            s = threadEvent.wait(secsToWait)
            if (s):
                    print_debug("is this being called?")
                    threadEvent.clear()
                    continue
            alert()


if __name__ == '__main__':
    # Create and start a thread
    tts.init()
    currentEvent = get_next_event()

    # Start the thread that 
    secondary_thread = threading.Thread(target=main_wait_thread, args=())
    secondary_thread.start()
    check_for_changes_to_calendar_thread()
