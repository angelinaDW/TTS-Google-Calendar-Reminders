import pyttsx3

engine = pyttsx3.init()
def readText(s):
    engine.say(s)
    engine.runAndWait()


volume = engine.getProperty('volume')   #getting to know current volume level (min=0 and max=1)
engine.setProperty('volume',2.0) 
print (volume)      
