#! /usr/bin/python3

# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    import RPi.GPIO as GPIO
except:
    _hwLoaded = False

import tkinter as tk
from tkinter import ttk
from Erl2Toggle import Erl2Toggle

class Erl2Heater(Erl2Toggle):

    def __init__(self,
                 displayLocs=[],
                 buttonLoc={},
                 displayImages=['button-grey-30.png','button-red-30.png'],
                 buttonImages=['radio-off-red-30.png','radio-on-red-30.png'],
                 label='Heater',
                 erl2context={}):

        # call the Erl2Toggle class's constructor
        super().__init__(controlType='heater',
                         displayLocs=displayLocs,
                         buttonLoc=buttonLoc,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2context=erl2context)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or self.erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # read this useful parameter from Erl2Config
        self.__gpioChannel = self.erl2context['conf'][self.controlType]['gpioChannel']

        # set up the heater relay hardware...
        if _hwLoaded:

            # we're using GPIO.BCM (channel numbers) not GPIO.BOARD (pin numbers on the pi)
            GPIO.setmode(GPIO.BCM)

            # silence the annoying GPIO warnings about channels having already been set up
            GPIO.setwarnings(False)

            # set up the heater relay channel for output
            GPIO.setup(self.__gpioChannel, GPIO.OUT)

            # set the channel's state explicitly, to match our logical state
            GPIO.output(self.__gpioChannel, self.state)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Heater or a child class)
        if self.__class__.__name__ == 'Erl2Heater':
            self.updateLog()

    def changeHardwareState(self):

        # apply the new state to the relay hardware
        #print (f"{self.__class__.__name__}: Debug: changing to state [{self.state}] on GPIO channel [{self.__gpioChannel}]")
        if _hwLoaded:
            GPIO.output(self.__gpioChannel, self.state)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Heater',font='Arial 30 bold').grid(row=0,column=0)
    heater = Erl2Heater(displayLocs=[{'parent':root,'row':1,'column':0}],
                        buttonLoc={'parent':root,'row':2,'column':0})
    heater.setActive()
    root.mainloop()

if __name__ == "__main__": main()

