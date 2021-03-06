from __future__ import print_function

from sqlalchemy import true
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
getTimeOfDay = datetimeUtils.getTimeOfDay
from plyer import notification
import random

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Settings
CHECK_FOR_CHANGES_TO_CAL_DELAY = 4 # How often to check for changes to the calendar, in seconds
DESKTOP_NOTIFICATIONS = True # Whether to also send desktop notifications
NOTIFY_WHEN_EVENT_IS_ALMOST_OVER = True # Whether to let the user know when their event is almost over
NOTIFY_WHEN_EVENT_IS_OVER = True # Whether to let the user know when their event ends
WARN_USER_EARLY = True
minutesBeforeToAlert = 3 # How many minutes in advance the computer should warn the user before an event
minutesBeforeEndAlert = 5
user = "Angelina" # The name you would like the "AI" to call you
greetings = [f"Hi there {user}!", f"Good {getTimeOfDay()} {user}!", f"Greetings {user}! Nice to see you again."]
DEBUG_MODE = False # If debug mode is false, debug messages won't be printed

# Variables local to this module that don't have to do with settings
waitForAlarmThread = None # The thread that waits for alarms to go off
eventsToday = [] # A list of event objects containing all the events under today
creds = None
service = None

calendarChangedFromAbove = Event() # Invoked when new changes are found from the google calendar
saySomethingEvent = Event() # Invoked when we want to have the tts run something
whatToSay = ""

def printd(msg):
    # Prints the given message only if DEBUG_MODE is set to true
    if DEBUG_MODE == True:
        print(msg)
    

def say(what):
    # schedules the main thread to say something
    # Also show a notification, if the user's preferences are set to do so
    print("made it to say")
    notification.notify(title="Upcoming Event", message=what, app_icon=None, timeout=20)
    tts.readText(what)
    print("exiting say")

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

def getAllEventsToday() -> list[dict]:
    '''
    Returns a list of all the events currently scheduled for today
    '''
    # Call the Calendar API
    if creds == None:
        print("Loggging the user in...")
        auth_user()
        print("Login sucessful.")
    service = build('calendar', 'v3', credentials=creds)
    page_token = None
    now = datetime.datetime.utcnow().isoformat() + "Z"
    #print("now: " + str(now))
    endOfDay = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day + 1, 0)
    endOfDayUTC = naiveLocalDateTimeToUTC(endOfDay)
    
    #print("----")
    #print(endOfDayUTC.isoformat())
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=(endOfDayUTC.isoformat()), pageToken = page_token,
                                            maxResults=250, singleEvents=True,
                                            orderBy='startTime').execute()
    events = events_result.get('items', [])
    '''
    #print("Events before weeding")
    for e in events:
        print(e['summary'])
    '''
    events = [e for e in events if not isAllDayEvent(e) and secondsFromNowUntilDT(stringToDateTime(e['start'].get("dateTime"))) > 0]
    page_token = events_result.get("nextPageToken")
    '''
    print("Events after weeding")
    for e in events:
        print(e['summary'])
    print(f"Are there more events available? {page_token != None}")
    '''
    return events


# Poorly-named function, as this also handles text-to-speech
def checkForChangesToCalendar():
    global eventsToday
    while True:
        if (saySomethingEvent.is_set()):
            print("Speaking...")
            tts.readText(whatToSay)
            saySomethingEvent.clear()
        print_debug("In checking-for-changes thread")
        if (getAllEventsToday() != eventsToday):
            print("Calendar changes detected.")
            # Tell the other thread it needs to restart
            calendarChangedFromAbove.set()
            eventsToday = getAllEventsToday()
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
    #global currentCalendarEvent # allow us to actually access and modify currentCalendarEvent from inside this funciton
    #print_debug(f"currentCalendarEvent " + str(currentCalendarEvent))
    print("In waitforAlarmThread")
    restart_flag = False
    global eventsToday
    eventsToday = getAllEventsToday()
    for calEvent in eventsToday:
        addEventAlarmsToQueue(calEvent)
    alarmsQueue.sort() # Sort the alarms in order
    # Let's verify that this worked properly
    for a in alarmsQueue:
        print(a)


    while len(alarmsQueue) > 0:
        upcomingAlarm: alarm.Alarm = alarmsQueue.take() # Takes the alarm who has been in line the longest out of line
        print(f"upcomingAlarm: {upcomingAlarm}")
        
        
        # If the alarm technically already happened, but we are in a buffer zone, go off now
        if upcomingAlarm.hasAlreadyPassed() and upcomingAlarm.minutesSincePassed() <= alarm.MAX_LATE_GOOFF:
            print("alarm has already passed")
            upcomingAlarm.goOff()
            print("made ithere?")
            continue
        elif upcomingAlarm.hasAlreadyPassed():
            continue # skip this alarm, it's too late now
        else:   # Wait until alarm
            print("Time until next alarm: " + str(upcomingAlarm.timeLeft()/60) + " minutes")
            datetimeUtils.waitUntilDatetimeOrEvent(upcomingAlarm.goOffTime, calendarChangedFromAbove, timeExpiredCallback = upcomingAlarm.goOff, eventTriggeredCallback = onCalendarSync, calEvent = upcomingAlarm.event)
        print("we should make it here")

    print("we should make it down here after calendar updated or event goes off")
    waitForAlarmThread()
def onCalendarSync(calEvent: dict):
    calendarChangedFromAbove.clear() # Reset the flag
    global eventsToday
    global alarmsQueue
    eventsToday = getAllEventsToday() 

    alarmsQueue.clear()
    #print("here i am")

if __name__ == '__main__':
    # Create and start a thread
    tts.readText(greetings[random.randrange(0, len(greetings))])
    
    print("Getting today's events...")
    eventsToday = getAllEventsToday()
    # Start the thread that 
    wThread = threading.Thread(target=waitForAlarmThread, args=())
    wThread.start()
    checkForChangesToCalendar()
