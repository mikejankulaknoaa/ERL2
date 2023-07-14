#! /usr/bin/python3

from datetime import datetime as dt
from datetime import timezone as tz
from random import random as random
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2Sensor():

    def __init__(self,
                 sensorType='generic',
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 erl2conf=None,
                 img=None):

        self.sensorType = sensorType
        self.__displayLocs = displayLocs
        self.__statusLocs = statusLocs
        self.__correctionLoc = correctionLoc
        self.erl2conf = erl2conf

        # remember what widgets are active for this sensor
        self.__displayWidgets = []
        self.__statusWidgets = []
        self.__correctionWidgets = []

        # for a sensor, we track current value and last valid update time
        # (be careful to update these values only in the measure() method)
        self.online = True
        self.value = {}
        self.lastValid = None

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if self.erl2conf is None:
            self.erl2conf = Erl2Config()
            #if 'tank' in self.erl2conf.sections() and 'id' in self.erl2conf['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2conf['tank']['id']}]")

        # if this gets instantiated somehow as 'generic', these parameters aren't in the config
        self.__sampleFrequency = 5
        self.__loggingFrequency = 300
        self.__displayParameter = 'generic'
        self.__displayDecimals = 3
        self.__offsetDefault = 0.

        # but for real sensors, load them from Erl2Config
        if self.sensorType != 'generic':
            self.__sampleFrequency = self.erl2conf[self.sensorType]['sampleFrequency']
            self.__loggingFrequency = self.erl2conf[self.sensorType]['loggingFrequency']
            self.__displayParameter = self.erl2conf[self.sensorType]['displayParameter']
            self.__displayDecimals = self.erl2conf[self.sensorType]['displayDecimals']
            self.__offsetDefault = self.erl2conf[self.sensorType]['offsetDefault']

        # start a data/log file for the sensor
        if not self.erl2conf['system']['disableFileLogging']:
            self.dataLog = Erl2Log(logType='sensor', logName=self.sensorType, erl2conf=self.erl2conf)
        else:
            self.dataLog = None

        # loop through the list of needed display widgets for this sensor
        for loc in self.__displayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text='--', font='Arial 40 bold', foreground='#1C4587')
            l.grid(row=0, column=0, sticky='nwse')

            # keep a list of display widgets for this sensor
            self.__displayWidgets.append(l)

        # loop through the list of needed status widgets for this sensor
        for loc in self.__statusLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nw')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text='--', font='Arial 16', foreground='#1C4587')
            l.grid(row=0, column=0, sticky='nw')

            # keep a list of status widgets for this sensor
            self.__statusWidgets.append(l)

        # create the correction widgets' base frame as a child of its parent
        f = ttk.Frame(self.__correctionLoc['parent'], padding='0 0', relief='solid', borderwidth=0)
        f.grid(row=self.__correctionLoc['row'], column=self.__correctionLoc['column'], padx='2', pady='0', sticky='nw')

        # create the entry field for the correction offset
        e = ttk.Entry(f, width=4, font='Arial 20',justify='right')
        e.insert(tk.END, self.__offsetDefault)
        e.grid(row=0,column=1, sticky='e')
        #e.bind('<FocusIn>', self.numpadEntry)
        #e.selection_range(0,0)
        e.config(state='disabled')

        # this is the Label shown beside the entry widget
        ttk.Label(f, text='Offset', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, padx='2 2', sticky='w')

        #self.__correctionWidgets.append(e)

        # add a Label widget to show the raw sensor value
        l = ttk.Label(f, text='--', font='Arial 16', justify='right')
        l.grid(row=1, column=1, sticky='e')

        ttk.Label(f, text='Raw Value', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(row=1, column=0, padx='2 2', sticky='w')

        self.__correctionWidgets.append(l)

        ## add a Label widget to show the corrected sensor value
        #l = ttk.Label(f, text='--', font='Arial 16', justify='right')
        #l.grid(row=2, column=1, sticky='e')

        #ttk.Label(f, text='Corrected', font='Arial 14'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=2, column=0, padx='2 2', sticky='w')

        #self.__correctionWidgets.append(l)

        f.rowconfigure(0,weight=1)
        f.rowconfigure(1,weight=1)
        #f.rowconfigure(2,weight=1)
        f.columnconfigure(1,weight=1)
        f.columnconfigure(0,weight=0)

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Sensor or a child class)
        if self.__class__.__name__ == 'Erl2Sensor':
            self.readSensor()

    def readSensor(self):

        # take a measurement
        currentTime, measurement, online = self.measure()

        #print (f"{self.__class__.__name__}: Debug: readSensor() receiving [{str(currentTime)}][{str(measurement)}][{str(online)}]")

        # update the display widgets with their current values
        self.updateDisplays(self.__displayWidgets,self.__statusWidgets,self.__correctionWidgets)

        # how long before we should update the display widgets again?
        delay = (int(
                  (
                    (
                      int(
                        currentTime.timestamp()  # timestamp in seconds
                        / self.__sampleFrequency # convert to number of intervals of length sampleFrequency
                      )                          # truncate to beginning of previous interval (past)
                    + 1)                         # advance by one time interval (future)
                    * self.__sampleFrequency     # convert back to seconds/timestamp
                    - currentTime.timestamp()    # calculate how many seconds from now to next interval
                    )
                  * 1000)                        # convert to milliseconds, then truncate to integer
                )

        # update the display widgets again after waiting an appropriate number of milliseconds
        self.__displayWidgets[0].after(delay, self.readSensor)

        # is this one of the data values that should be written to the log file?
        if not self.erl2conf['system']['disableFileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

                # send the new sensor data to the log (in dictionary form)
                if self.dataLog is not None:
                    self.dataLog.writeData(measurement)

            # if the next file-writing interval time is empty or in the past, update it
            if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
                self.__nextFileTime = (
                  (
                    int(
                      currentTime.timestamp()   # timestamp in seconds
                      / self.__loggingFrequency # convert to number of intervals of length loggingFrequency
                    )                           # truncate to beginning of previous interval (past)
                  + 1)                          # advance by one time interval (future)
                  * self.__loggingFrequency     # convert back to seconds/timestamp
                )

    def updateDisplays(self, displayWidgets, statusWidgets, correctionWidgets):

        #print (f"{self.__class__.__name__}: Debug: updateDisplays() using [{str(self.lastValid)}][{str(self.value)}][{str(self.online)}]")

        # figure out what value to use in update
        if not self.online:
            upd = '--'
            #if self.sensorType == 'pH':
            #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] is offline")

        elif len([x for x in self.value.keys() if 'Timestamp' not in x]) == 0:
            upd = '--'
            #if self.sensorType == 'pH':
            #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] value is empty")

        elif self.__displayParameter not in self.value:
            raise AttributeError(f"{self.__class__.__name__}: Error: no key named [{self.__displayParameter}] in self.value")

        else:
            # even if the parameter is present, it might not be in float format
            try:
                upd = f"{float(round(self.value[self.__displayParameter],self.__displayDecimals)):.{self.__displayDecimals}f}"
                #if self.sensorType == 'pH':
                #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] update is [{upd}]")
            except:
                upd = '--'
                #if self.sensorType == 'pH':
                #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] float exception for [{self.value[self.__displayParameter]}][{self.__displayDecimals}]")

        # loop through all placements of this sensor's display widgets
        for w in displayWidgets + correctionWidgets:

            # update the display
            w.config(text=upd)

        # the status message conveys information about how current the reading is and on/offline status
        if self.lastValid is not None:
            upd = self.lastValid.astimezone(self.erl2conf['system']['timezone']).strftime(self.erl2conf['system']['dtFormat'])
        else:
            upd = 'never'

        if self.online:
            fnt = 'Arial 14'
            fgd = '#1C4587'
        else:
            fnt = 'Arial 14 bold'
            fgd = '#A93226'

        #fnt = 'Arial 14 bold'
        #fgd = '#A93226'

        # loop through all placements of this sensor's status widgets
        for w in self.__statusWidgets:

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)

    def getTimestamp(self):

        # record the current timestamp
        currentTime = dt.now(tz=tz.utc)

        # add timestamps to a template measurement dict
        m = {'Timestamp.UTC': currentTime.strftime(self.erl2conf['system']['dtFormat']),
             'Timestamp.Local': currentTime.astimezone(self.erl2conf['system']['timezone']).strftime(self.erl2conf['system']['dtFormat'])}

        return currentTime, m

    # placeholder method -- must be overwritten in child classes
    def measure(self):

        # fake measurement
        self.value = {'generic':random()}

        # fake sensor never goes offline
        self.online = True

        # add Timestamps to measurement record
        t, m = self.getTimestamp()

        # produce the final measurement dict with timestamps and values
        self.value = {**m, **self.value}

        # remember timestamp of last valid measurement
        self.lastValid = t

        #print (f"{self.__class__.__name__}: Debug: measure() returning [{str(t)}][{str(self.value)}][{str(self.online)}]")

        # return timestamp, measurement and status
        return t, self.value, self.online

def main():

    root = tk.Tk()
    sensor = Erl2Sensor(displayLocs=[{'parent':root,'row':0,'column':0}],
                        statusLocs=[{'parent':root,'row':1,'column':0}],
                        correctionLoc={'parent':root,'row':2,'column':0})
    root.mainloop()

if __name__ == "__main__": main()

