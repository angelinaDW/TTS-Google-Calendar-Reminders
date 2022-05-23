import pyttsx3

engine = None
def init():
    global engine   
    engine = pyttsx3.init()
def readText(s):
    print(engine == None)
    print("TTS running")
    engine.say(s)
    engine.runAndWait()
    print("TTS done")
