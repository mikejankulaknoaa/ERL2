#! /usr/bin/python3

from datetime import datetime as dt
from math import ceil,cos,pi
import tkinter as tk
from tkinter import ttk
from Erl2Sensor import Erl2Sensor

# this is a 'virtual' temperature sensor designed to be reactive to heater/chiller controls
class Erl2VirtualTemp(Erl2Sensor):

    def __init__(self,
                 parent=None,
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 stack=0,
                 channel=1,
                 erl2conf=None,
                 img=None):

        # call the Erl2Sensor class's constructor
        super().__init__(type='virtualtemp',
                         displayLocs=displayLocs,
                         statusLocs=statusLocs,
                         correctionLoc=correctionLoc,
                         erl2conf=erl2conf,
                         img=img)

        # private attributes specific to Erl2VirtualTemp
        self.__parent = parent
        self.__midpoint = 26.
        self.__range = 1.

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2VirtualTemp or a child class)
        if self.__class__.__name__ == 'Erl2VirtualTemp':
            self.readSensor()

    def measure(self):

        # the local time
        local = dt.now()

        # how far into the current day are we?
        day = ((float(local.strftime('%-H'))/60. + float(local.strftime('%-M')))/60. + float(local.strftime('%-S')))/24.

        # figure out the external temperature we're equilibrating towards, at this hour
        targetTemp = self.__midpoint - cos( day * 2. * pi ) * self.__range

        # remember the previous value
        if 'temp.degC' in self.value:
            prevTemp = self.value['temp.degC']
        else:
            # at startup, assign tank temp to be environmental temp
            prevTemp = targetTemp

        # initialize the measurement result
        self.value = {}

        # sneak a peak at whether the system has the heater or chiller turned on
        try:
            heaterOn = self.__parent.controls['heater'].state
            chillerOn = self.__parent.controls['chiller'].state
        except:
            heaterOn = 0
            chillerOn = 0

        # temperature change: react to heater/chiller
        if heaterOn or chillerOn:
            if heaterOn and chillerOn:
                delta = 0
            elif heaterOn:
                delta = 0.02
            elif chillerOn:
                delta = -0.02

            # simulate the effect of heater and chiller
            self.value['temp.degC'] = prevTemp + delta

        # temperature: gradually approach environmental temp
        else:
            delta = ceil( ( 0.0015 ** ( -abs( (prevTemp-targetTemp)/50.))) * 100.) / 100.

            # limit the magnitude of the effect of environment equilibration
            delta = min(0.001, delta)

            # apply the delta
            if targetTemp >= prevTemp:
                self.value['temp.degC'] = prevTemp + delta
            else:
                self.value['temp.degC'] = prevTemp - delta

        # virtual sensor never goes offline
        self.online = True

        # add Timestamps to measurement record
        t, m = self.getTimestamp()

        # produce the final measurement dict with timestamps and values
        self.value = {**m, **self.value}

        # remember timestamp of last valid measurement
        self.lastValid = t

        #print (f"{self.__class__.__name__}: Debug: measure() before [{prevTemp}], offset [{delta}], after [{self.value['temp.degC']}]")

        # return timestamp, measurement and status
        return t, self.value, self.online

def main():

    root = tk.Tk()
    virtualtemp = Erl2VirtualTemp(displayLocs=[{'parent':root,'row':0,'column':0}],
                                  statusLocs=[{'parent':root,'row':1,'column':0}])
    root.mainloop()

if __name__ == "__main__": main()
