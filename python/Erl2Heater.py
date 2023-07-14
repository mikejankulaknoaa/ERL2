#! /usr/bin/python3

import RPi.GPIO as GPIO
import tkinter as tk
from tkinter import ttk
from Erl2Toggle import Erl2Toggle

class Erl2Heater(Erl2Toggle):

    def __init__(self,
                 displayLocs=[],
                 buttonLocs=[],
                 displayImages=['button-grey-30.png','button-red-30.png'],
                 buttonImages=['radio-off-red-30.png','radio-on-red-30.png'],
                 label='Heater',
                 channel=None,
                 erl2context={}):

        # call the Erl2Toggle class's constructor
        super().__init__(type='heater',
                         displayLocs=displayLocs,
                         buttonLocs=buttonLocs,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2context=erl2context)

        # private attributes specific to Erl2Heater
        self.__channel = channel

        # set up the heater relay hardware...

        # the default channel for the ERL2 heater is 23 (pin #16, and we use pin #14 as ground)
        if self.__channel is None:
            self.__channel = 23

        # we're using GPIO.BCM (channel numbers) not GPIO.BOARD (pin numbers on the pi)
        GPIO.setmode(GPIO.BCM)

        # silence the annoying GPIO warnings about channels having already been set up
        GPIO.setwarnings(False)

        # set up the heater relay channel for output
        GPIO.setup(self.__channel, GPIO.OUT)

        # set the channel's state explicitly, to match our logical state
        GPIO.output(self.__channel, self.state)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Heater or a child class)
        if self.__class__.__name__ == 'Erl2Heater':
            self.updateLog()

    def changeHardwareState(self):

        # apply the new state to the relay hardware
        #print (f"{self.__class__.__name__}: Debug: changing to state [{self.state}] on channel [{self.__channel}]")
        GPIO.output(self.__channel, self.state)

def main():

    root = tk.Tk()
    heater = Erl2Heater(displayLocs=[{'parent':root,'row':0,'column':0}],
                        buttonLocs=[{'parent':root,'row':1,'column':0}])
    heater.setActive()
    root.mainloop()

if __name__ == "__main__": main()

