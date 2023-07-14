#! /usr/bin/python3

from megaind import get4_20In
import tkinter as tk
from tkinter import ttk
from Erl2Sensor import Erl2Sensor

# ProSense Pt100 temperature transmitter XTP25N-100-0100C
class Erl2Temperature(Erl2Sensor):

    def __init__(self,
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 erl2conf=None,
                 img=None):

        # call the Erl2Sensor class's constructor
        super().__init__(type='temperature',
                         displayLocs=displayLocs,
                         statusLocs=statusLocs,
                         correctionLoc=correctionLoc,
                         erl2conf=erl2conf,
                         img=img)

        # read in the system configuration file if needed
        if self.erl2conf is None:
            self.erl2conf = Erl2Config()
            #if 'tank' in self.erl2conf.sections() and 'id' in self.erl2conf['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2conf['tank']['id']}]")

        # private attributes specific to Erl2Temperature
        self.__stack = self.erl2conf['temperature']['stackLevel']
        self.__channel = self.erl2conf['temperature']['inputChannel']

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Temperature or a child class)
        if self.__class__.__name__ == 'Erl2Temperature':
            self.readSensor()

    def measure(self):

        # initialize the measurement result
        self.value = {}

        # milliAmps are read from the input channel
        milliAmps = get4_20In(self.__stack, self.__channel)

        # validate result: by definition this should be between 4 and 20 mA
        if milliAmps >= 4. and milliAmps <= 20.:

            # add milliAmps to the results
            self.value['temp.mA'] = milliAmps

            # convert from 4-20 mA to 0-100 degC
            self.value['temp.degC'] = (self.value['temp.mA'] - 4.) * 100. / 16.

        # check if we're still/currently offline
        self.online = not (self.value == {})

        # add Timestamps to measurement record
        t, m = self.getTimestamp()

        # produce the final measurement dict with timestamps and values
        self.value = {**m, **self.value}

        # remember timestamp of last valid measurement
        if self.online:
            self.lastValid = t

        #print (f"{self.__class__.__name__}: Debug: measure() returning [{str(t)}][{str(self.value)}][{str(self.online)}]")

        # return timestamp, measurement and status
        return t, self.value, self.online

def main():

    root = tk.Tk()
    temperature = Erl2Temperature(displayLocs=[{'parent':root,'row':0,'column':0}],
                                  statusLocs=[{'parent':root,'row':1,'column':0}])
    root.mainloop()

if __name__ == "__main__": main()

