from datetime import datetime as dt
from math import ceil,cos,pi
import tkinter as tk
from tkinter import ttk
from Erl2Sensor import Erl2Sensor
from Erl2State import Erl2State

# this is a 'virtual' temperature sensor designed to be reactive to heater/chiller controls
class Erl2VirtualTemp(Erl2Sensor):

    def __init__(self,
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 label=None,
                 stack=0,
                 channel=1,
                 erl2context={}):

        # call the Erl2Sensor class's constructor
        super().__init__(sensorType='virtualtemp',
                         displayLocs=displayLocs,
                         statusLocs=statusLocs,
                         correctionLoc=correctionLoc,
                         label=label,
                         erl2context=erl2context)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # private attributes specific to Erl2VirtualTemp
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
        day = ((float(local.strftime('%H'))/60. + float(local.strftime('%M')))/60. + float(local.strftime('%S')))/24.

        # figure out the external temperature we're equilibrating towards, at this hour
        targetTemp = self.__midpoint - cos( day * 2. * pi ) * self.__range

        # remember the previous value
        if 'temp.degC' in self.value:
            prevTemp = self.value['temp.degC']
        else:
            # at startup, try to load a recently-logged temp, then just assign tank temp to be environmental temp
            prevTemp = self.erl2context['state'].get(self.sensorType,'value',targetTemp)
            #print (f"{self.__class__.__name__}: Debug: measure() reading [{prevTemp}] from state file")

        # initialize the measurement result
        self.value = {}

        # sneak a peak at whether the system has the heater or chiller turned on
        try:
            heaterOn = self.erl2context['conf']['sensors']['heater'].setting
            chillerOn = self.erl2context['conf']['sensors']['chiller'].setting
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

        # apply the corrective offset
        self.applyOffset(self.value, updateRaw=True)

        # return timestamp, measurement and status
        return t, self.value, self.online

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2VirtualTemp',font='Arial 30 bold').grid(row=0,column=0)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0)
    ttk.Label(statusFrame,text='Virtual Temp last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')

    virtualtemp = Erl2VirtualTemp(displayLocs=[{'parent':root,'row':1,'column':0}],
                                  statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                                  correctionLoc={'parent':root,'row':2,'column':0})
    root.mainloop()

if __name__ == "__main__": main()

