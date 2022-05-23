from __future__ import print_function
import datetimeUtils
from datetimeUtils import*
from googleCalendarEvent import*
import datetime
from re import S
import time
import os.path
import textToSpeech as tts
import threading
from threading import Event
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime as dt
from myCoolQueue import myCoolQueue



SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Settings
CHECK_FOR_CHANGES_TO_CAL_DELAY = 15 # How often to check for changes to the calendar, in seconds

NOTIFY_WHEN_EVENT_IS_ALMOST_OVER = True # Whether to let the user know when their event is almost over
NOTIFY_WHEN_EVENT_IS_OVER = True # Whether to let the user know when their event ends
WARN_USER_EARLY = True
minutesBeforeToAlert = 5 # How many minutes in advance the computer should warn the user before an event
minutesBeforeEndAlert = 5
user = "Username" # The name you would like the "AI" to call you
greetings = [f"Hey there {user}!", f"Good {getTimeOfDay()}, {user}!", "Hey {user}! Nice to see you again."]

DEBUG_MODE = False # If debug mode is false, debug messages won't be printed

# Variables local to this module that don't have to do with settings
waitForAlarmThread = None
eventsToday = [] # A list of event objects containing all the events under today
creds = None
service = None
currentCalendarEvent = None

calendarChangedFromAbove = Event() # Invoked when new changes are found from the google calendar
saySomethingEvent = Event() # Invoked when we want to have the tts run something
whatToSay = ""

def schedule_say(what):
    # schedules the main thread to say something
    global whatToSay
    global saySomethingEvent
    whatToSay = what
    print(whatToSay)
    saySomethingEvent.set()

import alarm


alarmsQueue = myCoolQueue() # A queue of Alarm objects

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

# Returns the next event
def getNextCalendarEvent():
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

            if (isAllDayEvent(event) or secondsFromNowUntilDT(stringToDateTime(event['start'].get("dateTime"))) < 0):
                print_debug(f"{event['summary']} is all-day, or already happened.")
            else:
                print_debug(f"{event['summary']} is a non-all day event that hasn't happened yet.")
                return event
            if not event:
                print('No upcoming events found.')
                return



# Poorly-named function, as this also handles text-to-speech
def checkForChangesToCalendar():
    global currentCalendarEvent
    while True:
        if (saySomethingEvent.is_set()):
            print("Speaking...")
            tts.readText(whatToSay)
            saySomethingEvent.clear()
        print_debug("In checking-for-changes thread")
        next_e = getNextCalendarEvent()
        print_debug(f"New event: {next_e['summary']} Current event: {currentCalendarEvent['summary']}")
        if (next_e != currentCalendarEvent):
            print("Local calendar synced with Google Calendar.")
            # Tell the other thread it needs to restart
            calendarChangedFromAbove.set()
            currentCalendarEvent = getNextCalendarEvent()
            # Calendar updated
            
        else:
            print_debug("nope, current event is still the same")
        saySomethingEvent.wait(CHECK_FOR_CHANGES_TO_CAL_DELAY)

def addEventAlarmsToQueue(e: dict):
    '''
    Adds alarms to the queue of event e. 
    Which alarms will be added depends on the user's settings.
    '''
    if (WARN_USER_EARLY):
        alarmsQueue.append( alarm.Alarm( XMinutesBeforeAfter(stringToDateTime(e['start'].get('dateTime') ), -minutesBeforeToAlert ), e, alarm.ALARMTYPE.early )   )
    
    
    alarmsQueue.append( alarm.Alarm( stringToDateTime(e['start'].get('dateTime') ), e, alarm.ALARMTYPE.onStart )   )
    if (NOTIFY_WHEN_EVENT_IS_ALMOST_OVER):
        alarmsQueue.append( alarm.Alarm( XMinutesBeforeAfter(stringToDateTime(e['end'].get('dateTime') ), -minutesBeforeToAlert ), e, alarm.ALARMTYPE.endSoon )   )
    if (NOTIFY_WHEN_EVENT_IS_OVER):
        alarmsQueue.append( alarm.Alarm( stringToDateTime(e['end'].get('dateTime') ), e, alarm.ALARMTYPE.onEnd )   )
   
def waitForAlarmThread():
    global currentCalendarEvent # allow us to actually access and modify currentCalendarEvent from inside this funciton
    print_debug(f"currentCalendarEvent " + str(currentCalendarEvent))
    while True:
        print_debug("In notification/alarm thread.")
        currentCalendarEvent = getNextCalendarEvent()
        # Adds the alarms we care about (determined based on the user's settings) to the queue for this event
        addEventAlarmsToQueue(currentCalendarEvent)
        
        print(f"Upcoming event: {currentCalendarEvent['summary']} ")

        while len(alarmsQueue) > 0:
            upcomingAlarm: alarm.Alarm = alarmsQueue.take() # Takes the alarm who has been in line the longest out of line
            
            if upcomingAlarm.hasAlreadyPassed() and upcomingAlarm.minutesSincePassed() <= alarm.MAX_LATE_GOOFF: # If the alarm was supposed to already happen, but it's in a "buffer zone" where it can go off late...
                print("alarm has already passed")
                upcomingAlarm.goOff()
            elif upcomingAlarm.hasAlreadyPassed():
                continue # skip this alarm, it's too late now
            else:   
                datetimeUtils.waitUntilDatetimeOrEvent(upcomingAlarm.goOffTime, calendarChangedFromAbove, upcomingAlarm.goOff, onCalendarSync)
            
def onCalendarSync():
    alarmsQueue.clear() # clear the queue so that we can rebuild it next time
    calendarChangedFromAbove.clear() # mark the event as having already happened

if __name__ == '__main__':
    # Create and start a thread
    tts.init()
    tts.readText(greetings[1])
    currentCalendarEvent = getNextCalendarEvent()

    # Start the thread that 
    waitForAlarmThread = threading.Thread(target=waitForAlarmThread, args=())
    waitForAlarmThread.start()
    checkForChangesToCalendar()
