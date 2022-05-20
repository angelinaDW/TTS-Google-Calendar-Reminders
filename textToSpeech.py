import pyttsx3

engine = pyttsx3.init()
def readText(s):
    engine.say(s)
    engine.runAndWait()


