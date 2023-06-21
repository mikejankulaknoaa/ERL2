#! /usr/bin/python3

from datetime import datetime
from random import random
from tkinter import *
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2Sensor():

    def __init__(self, parent, clones=[], type='generic', row=0, column=0, erl2conf=None):
        self.__parent = parent
        self.__clones = clones
        self.__sensorType = type
        self.__row = row
        self.__column = column
        self.__erl2conf = erl2conf

        # these attributes are merely placeholders
        self.value = {}
        self.value['generic1'] = None
        self.value['generic2'] = None

        # remember what widgets are active in showing the sensor's current value
        self.__sensorDisplays = []

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # start a data/log file for the sensor; we will track milliAmps and deg Celsius
        if self.__erl2conf['system']['fileLogging']:
            self.dataLog = Erl2Log(logType='sensor', logName=self.__sensorType, erl2conf=self.__erl2conf)
        else:
            self.dataLog = None

        # loop through the sensor's primary parents and all of its clones
        for par in [self.__parent] + self.__clones:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(par, padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=self.__row, column=self.__column, padx='2', pady='2', sticky='nwse')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text='0.0', font='Arial 40 bold', foreground='#1C4587')
            l.grid(row=0, column=0, sticky='nwse')
            #f.rowconfigure(0,weight=1)
            #f.columnconfigure(0,weight=1)

            # keep a list of label widgets for this sensor
            self.__sensorDisplays.append(l)

    def readSensor(self):

        # take a measurement
        m = self.measure()

        # remember the timestamp at the exact moment of measurement
        self.datetime = datetime.utcnow()
        m = {'Timestamp': self.datetime.strftime(self.__erl2conf['system']['dtFormat']), **m}

        # update the display widget(s)
        self.updateDisplays(self.__sensorDisplays)

        # how long before we should update the display widget again?
        delay = (int(
                  (
                    (
                      int(
                        self.datetime.timestamp()                               # timestamp in seconds
                        / self.__erl2conf[self.__sensorType]['sampleFrequency'] # convert to number of intervals of length sampleFrequency
                      )                                                         # truncate to beginning of previous interval (past)
                    + 1)                                                        # advance by one time interval (future)
                    * self.__erl2conf[self.__sensorType]['sampleFrequency']     # convert back to seconds/timestamp
                    - self.datetime.timestamp()                                 # calculate how many seconds from now to next interval
                    )
                  * 1000)                                                       # convert to milliseconds, then truncate to integer
                )

        # update the display widget(s) again after waiting an appropriate number of milliseconds
        self.__sensorDisplays[0].after(delay, self.readSensor)

        # is this one of the data values that should be written to the log file?
        if self.__erl2conf['system']['fileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and self.datetime.timestamp() > self.__nextFileTime:

                # send the new sensor data to the log (in dictionary form)
                if self.dataLog is not None:
                    self.dataLog.writeData(m)

            # if the next file-writing interval time is empty or in the past, update it
            if self.__nextFileTime is None or self.datetime.timestamp() > self.__nextFileTime:
                self.__nextFileTime = (
                  (
                    int(
                      self.datetime.timestamp()                                # timestamp in seconds
                      / self.__erl2conf[self.__sensorType]['loggingFrequency'] # convert to number of intervals of length loggingFrequency
                    )                                                          # truncate to beginning of previous interval (past)
                  + 1)                                                         # advance by one time interval (future)
                  * self.__erl2conf[self.__sensorType]['loggingFrequency']     # convert back to seconds/timestamp
                )

    def measure(self):
        # mimic a sensor reading
        self.value['generic1'] = random()

        # mimic a derived sensor value
        self.value['generic2'] = (1. - self.generic1) * 10.

        # return the measurement result as a dict
        # (key values will be used as headers in the output csv)
        return {'generic1': self.value['generic1'],
                'generic2': self.value['generic2']}

    def updateDisplays(self, widgets):
        # loop through all placements of this sensor's displays
        for w in widgets:

            # update the display
            w.config(text=f"{float(round(self.value['generic1'],3)):.{3}f}")

def main():

    root = Tk()
    sensor = Erl2Sensor(root)
    root.mainloop()

if __name__ == "__main__": main()

