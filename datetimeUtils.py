import datetime
from datetime import datetime as dt
from dateutil.parser import parse as dtparse
import threading
from threading import Event
from types import FunctionType
import pytz
from tzlocal import get_localzone


def secondsBetween(earlier: dt, later: dt) -> float:
    # print(f"ealier: {str(earlier)}")
    # print(f"later: {str(later)}")
    return (later - earlier).total_seconds()

def getCurDT() -> dt:
    n = dt.utcnow()
    n = pytz.utc.localize(n) 
    return n

def secondsFromNowUntilDT(d: dt) -> float:
    return secondsBetween(getCurDT(), d)

def XMinutesBeforeAfter(referenceDt: dt, minutesBeforeAfter: float) -> dt:
    '''
    Returns a new datetime object minutesBeforeAfter minutes before or after referenceDt
    For instance, if you pass in -5 for minutesBeforeAfter, it will return a datetime object 5 minutes before referenceDt
    '''
    return referenceDt + datetime.timedelta(minutes = minutesBeforeAfter)

def naiveLocalDateTimeToUTC(naive: dt):
     local = get_localzone().localize(naive)
     return local.astimezone(pytz.utc)

def getTimeOfDay() -> str:
    '''
    Returns a string of morning, afternoon, or evening based on the time of day
    '''
    print(type(dt))
    now = dt.now().time()
    morning = datetime.time(3, 0)
    afternoon = datetime.time(12,0)
    night = datetime.time(18, 0)

    if now >= morning and now < afternoon:
        return "morning"
    if now >= afternoon and now <= night:
        return "afternoon"
    else:
        return "evening"

def stringToDateTime(s: str) -> dt:
    d = dtparse(s)
    if d == None:
        raise Exception("Non-event passed to time_to_event!")
    return d

def waitUntilDatetimeOrEvent(d: dt, event: Event, timeExpiredCallback: FunctionType, eventTriggeredCallback: FunctionType, calEvent: dict):
    # Waits until either the current time >= dt, or event happens
    
    result = event.wait( secondsBetween(getCurDT(), d) )
    if (result): # if the event was triggered
        print("Event triggered")
        eventTriggeredCallback(calEvent)
    else:
        print("Time expired")
        timeExpiredCallback()