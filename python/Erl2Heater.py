# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    import RPi.GPIO as GPIO
except:
    _hwLoaded = False

import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Control import Erl2Control
from Erl2Useful import locDefaults

class Erl2Heater(Erl2Control):

    def __init__(self,
                 displayLocs=[],
                 buttonLoc={},
                 displayImages=['button-grey-30.png','button-red-30.png'],
                 buttonImages=['radio-off-red-30.png','radio-on-red-30.png'],
                 label='Heater',
                 erl2context={}):

        # controlType will be 'heater'
        controlType = 'heater'

        # hack up the displayLocs with heater-specific defaults before calling parent __init__
        heaterLocs = []
        for loc in displayLocs:
            heaterLocs.append(locDefaults(loc=loc,modDefaults={'relief':'flat','borderwidth':0, 'padx':'2','pady':'2'}))

        # read in the system configuration file if needed
        if 'conf' not in erl2context:
            erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # read this useful parameter from Erl2Config
        self.__gpioChannel = erl2context['conf'][controlType]['gpioChannel']

        # set up the heater relay hardware...
        if _hwLoaded:

            # we're using GPIO.BCM (channel numbers) not GPIO.BOARD (pin numbers on the pi)
            GPIO.setmode(GPIO.BCM)

            # silence the annoying GPIO warnings about channels having already been set up
            GPIO.setwarnings(False)

            # set up the heater relay channel for output
            GPIO.setup(self.__gpioChannel, GPIO.OUT)

            # set the channel's setting explicitly, to match our logical setting
            #GPIO.output(self.__gpioChannel, self.setting)

        # call the Erl2Control class's constructor
        super().__init__(controlType=controlType,
                         widgetType='button',
                         widgetLoc=buttonLoc,
                         displayLocs=heaterLocs,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2context=erl2context)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Heater or a child class)
        if self.__class__.__name__ == 'Erl2Heater':
            self.updateLog()

    def changeHardwareSetting(self):

        # apply the new setting to the relay hardware
        #print (f"{self.__class__.__name__}: Debug: changing heater to setting [{int(self.setting)}] on GPIO channel [{self.__gpioChannel}]")
        if _hwLoaded:
            GPIO.output(self.__gpioChannel, int(self.setting))

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Heater',font='Arial 30 bold').grid(row=0,column=0)
    heater = Erl2Heater(displayLocs=[{'parent':root,'row':1,'column':0}],
                        buttonLoc={'parent':root,'row':2,'column':0})
    heater.setActive()
    root.mainloop()

if __name__ == "__main__": main()

