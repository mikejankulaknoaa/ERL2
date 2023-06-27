#! /usr/bin/python3

from datetime import datetime as dt
from tkinter import *
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2Sensor():

    def __init__(self,
                 type='generic',
                 displayLocs=[],
                 parameter=None,
                 places=1,
                 erl2conf=None,
                 img=None):

        self.__sensorType = type
        self.__displayLocs = displayLocs
        self.__parameter = parameter
        self.__places = places
        self.__erl2conf = erl2conf

        next # remember what widgets are active for this sensor
        self.__displayWidgets = []

        # for a sensor, we track current value
        self.value = {}

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # start a data/log file for the sensor
        if self.__erl2conf['system']['fileLogging']:
            self.dataLog = Erl2Log(logType='sensor', logName=self.__sensorType, erl2conf=self.__erl2conf)
        else:
            self.dataLog = None

        # loop through the list of needed display widgets for this sensor
        for loc in self.__displayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text='---', font='Arial 40 bold', foreground='#1C4587')
            l.grid(row=0, column=0, sticky='nwse')

            # keep a list of display widgets for this sensor
            self.__displayWidgets.append(l)

    def readSensor(self):

        # take a measurement
        m = self.measure()

        # remember the timestamp at the exact moment of measurement
        currentTime = dt.utcnow()
        m = {'Timestamp': currentTime.strftime(self.__erl2conf['system']['dtFormat']), **m}

        # update the display widgets with their current values
        self.updateDisplays(self.__displayWidgets)

        # how long before we should update the display widgets again?
        delay = (int(
                  (
                    (
                      int(
                        currentTime.timestamp()                                 # timestamp in seconds
                        / self.__erl2conf[self.__sensorType]['sampleFrequency'] # convert to number of intervals of length sampleFrequency
                      )                                                         # truncate to beginning of previous interval (past)
                    + 1)                                                        # advance by one time interval (future)
                    * self.__erl2conf[self.__sensorType]['sampleFrequency']     # convert back to seconds/timestamp
                    - currentTime.timestamp()                                   # calculate how many seconds from now to next interval
                    )
                  * 1000)                                                       # convert to milliseconds, then truncate to integer
                )

        # update the display widgets again after waiting an appropriate number of milliseconds
        self.__displayWidgets[0].after(delay, self.readSensor)

        # is this one of the data values that should be written to the log file?
        if self.__erl2conf['system']['fileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

                # send the new sensor data to the log (in dictionary form)
                if self.dataLog is not None:
                    self.dataLog.writeData(m)

            # if the next file-writing interval time is empty or in the past, update it
            if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
                self.__nextFileTime = (
                  (
                    int(
                      currentTime.timestamp()                                  # timestamp in seconds
                      / self.__erl2conf[self.__sensorType]['loggingFrequency'] # convert to number of intervals of length loggingFrequency
                    )                                                          # truncate to beginning of previous interval (past)
                  + 1)                                                         # advance by one time interval (future)
                  * self.__erl2conf[self.__sensorType]['loggingFrequency']     # convert back to seconds/timestamp
                )

    def updateDisplays(self, displayWidgets):

        # loop through all placements of this sensor's display widgets
        for w in displayWidgets:

            # update the display
            if self.__parameter in self.value:
                w.config(text=f"{float(round(self.value[self.__parameter],self.__places)):.{self.__places}f}")
            else:
                raise AttributeError(f"{self.__class__.__name__}: Error: no key named [{self.__parameter}] in self.value")

    # placeholder method -- must be overwritten in child classes
    def measure(self):

        raise SystemError(f"{self.__class__.__name__}: Error: Erl2Sensor.measure() method must be overridden in child classes")

def main():

    root = Tk()
    sensor = Erl2Sensor(root)
    root.mainloop()

if __name__ == "__main__": main()

