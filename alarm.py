import datetimeUtils
from datetimeUtils import*
from main_refactored_using_queues import user, schedule_say
from enum import Enum
import datetime

MAX_LATE_GOOFF = 2 # In minutes, the max amount of time an alarm is allowed to go off that already passed, and was missed due to internet issues, or something
class ALARMTYPE(Enum):
    early = 1
    onStart = 2
    endSoon = 3
    onEnd = 4


class Alarm:

    def __init__(self, goOffDT : datetime.datetime, event: dict, t: ALARMTYPE) -> None:
        '''
        Parameters:


        Todo:
        - add more checks to make sure event actually is an event

        '''
        # Class variables
        assert type(goOffDT) == datetime.datetime; type(event) == dict; type(t) == ALARMTYPE

        self.goOffTime = goOffDT
        self.event = event
        if t not in ALARMTYPE:
            raise TypeError(f"{t} is not an ALARMTYPES!")
        self.type = t

        self.EARLY_MSG = f"Hey {user}! Your event {self.event['summary']} is starting in about { secondsFromNowUntilDT(stringToDateTime(self.event['start'].get('dateTime'))) //60 } minutes."
        self.START_MSG = f"Your event, {self.event['summary']} is starting now."
        self.END_SOON_MSG = f"Hey {user}! Your event {self.event['summary']} has about {secondsFromNowUntilDT(stringToDateTime(self.event['end'].get('dateTime')))/60 } minutes left."
        self.ON_EVENT_END_MSG = f"Your event, {self.event['summary']} has ended."
 


    
    def goOff(self):
        if (self.type == ALARMTYPE.early):
            s = self.EARLY_MSG
        elif self.type == ALARMTYPE.onStart:
            s = self.START_MSG
        elif self.type == ALARMTYPE.endSoon:
            s = self.START_MSG
        elif self.type == ALARMTYPE.onEnd:
            s = self.START_MSG  
        else:
            raise TypeError()
        schedule_say(s)
    
    def hasAlreadyPassed(self):
        '''
        Returns true if the time for the alarm to happen has already passed, false otherwise
        '''
        return self.minutesSincePassed() >= 0

    def minutesSincePassed(self) -> float:
        return datetimeUtils.secondsBetween(self.goOffTime, datetimeUtils.getCurDT())/60