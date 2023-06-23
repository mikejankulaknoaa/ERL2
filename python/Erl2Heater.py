#! /usr/bin/python3

import RPi.GPIO as GPIO
from Erl2Toggle import Erl2Toggle

class Erl2Heater(Erl2Toggle):

    def __init__(self, parent, clones=[], disableOn=[], channel=None, row=0, column=0, erl2conf=None, img=None):

        # call the Erl2Toggle class's constructor
        super().__init__(parent=parent,
                         clones=clones,
                         disableOn=disableOn,
                         type='heater',
                         row=row,
                         column=column,
                         label='Heater',
                         offImage='button-grey-30.png',
                         onImage='button-red-30.png',
                         erl2conf=erl2conf,
                         img=img)

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

        # start up the timing loop to log heater-related metrics to a log file
        self.updateLog()

    def changeHardwareState(self):

        # apply the new state to the relay hardware
        #print (f"{self.__class__.__name__}: Debug: changing to state [{self.state}] on channel [{self.__channel}]")
        GPIO.output(self.__channel, self.state)

def main():

    root = Tk()
    heater = Erl2Heater(root)
    root.mainloop()

if __name__ == "__main__": main()

