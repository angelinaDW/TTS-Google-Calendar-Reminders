def isAllDayEvent(e):
    '''
    Returns true if the argument passed in is both an event, and is NOT an all-day event.
    '''
    assert type(e) == dict
    try:
       dt = e['start'].get('dateTime')
       if dt == None:
           return True
       return False
    except ex:
        print(ex)
        return True
