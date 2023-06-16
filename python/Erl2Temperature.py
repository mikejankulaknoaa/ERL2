#! /usr/bin/python3

from datetime import datetime
import megaind as ind
from tkinter import *
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

# ProSense Pt100 temperature transmitter XTP25N-100-0100C
class Erl2Temperature():

    def __init__(self, parent, stack=0, channel=1, units='c', places=1, config=None):
        self.__parent = parent
        self.__stack = stack
        self.__channel = channel
        self.__units = units
        self.__places = places
        self.config = config

        # these attributes can be accessed outside the class
        self.tempMa = None
        self.tempC = None
        self.tempF = None

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if self.config is None:
            self.config = Erl2Config()
            if 'tank' in self.config.sections() and 'id' in self.config['tank']:
                print (f"Erl2Temperature: Tank Id is [{self.config['tank']['id']}]")

        # start a data/log file for the sensor; we will track milliAmps and deg Celsius
        if self.config['system']['fileLogging']:
            self.dataLog = Erl2Log(logType='sensor', logName='temperature', config=self.config)
        else:
            self.dataLog = None

        # create the temperature display's base frame as a child of its parent
        self.__frame = ttk.Frame(self.__parent, padding='2 2', relief='solid', borderwidth=1)
        self.__frame.grid(column=1, row=1, padx='2', pady='2', sticky='nwse')

        # add a Label widget to show the current temperature
        self.__tempDisplay = ttk.Label(self.__frame, text='0.0', font='Arial 40 bold', foreground='#1C4587')
        self.__tempDisplay.grid(column=1, row=1, sticky='nwse')
        self.__frame.columnconfigure(1,weight=1)
        self.__frame.rowconfigure(1,weight=1)

        # start the loop to update the temperature every 1s
        self.readTemperature()


    def readTemperature(self):
        # milliAmps are read from the input channel (remember timestamp)
        self.tempMa = ind.get4_20In(self.__stack, self.__channel)
        self.datetime = datetime.utcnow()

        # convert from 4-20 mA to 0-100 degC
        self.tempC = (self.tempMa - 4.) * 100. / 16.

        # convert degC to degF
        self.tempF = self.tempC * 9. / 5. + 32.

        # update the display (default is degC)
        if self.__units == 'f':
            self.__tempDisplay.config(text=f'{float(round(self.tempF,self.__places)):.{self.__places}f}')
        elif self.__units == 'ma':
            self.__tempDisplay.config(text=f'{float(round(self.tempMa,self.__places)):.{self.__places}f}')
        else:
            self.__tempDisplay.config(text=f'{float(round(self.tempC,self.__places)):.{self.__places}f}')

        # how long before we should update the temperature display again?
        delay = (int(
                  (
                    (
                      int(
                        self.datetime.timestamp()                       # timestamp in seconds
                        / self.config['temperature']['sampleFrequency'] # convert to number of intervals of length sampleFrequency
                      )                                                 # truncate to beginning of previous interval (past)
                    + 1)                                                # advance by one time interval (future)
                    * self.config['temperature']['sampleFrequency']     # convert back to seconds/timestamp
                    - self.datetime.timestamp()                         # calculate how many seconds from now to next interval
                    )
                  * 1000)                                               # convert to milliseconds, then truncate to integer
                )

        # update the temperature display again after waiting an appropriate number of milliseconds
        self.__tempDisplay.after(delay, self.readTemperature)

        # is this one of the data values that should be written to the log file?
        if self.config['system']['fileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and self.datetime.timestamp() > self.__nextFileTime:

                # send the new temperature data to the log (in dictionary form)
                if self.dataLog is not None:
                    self.dataLog.writeData({'Timestamp': self.datetime.strftime(self.config['system']['dtFormat']),
                                            'milliAmps': self.tempMa,
                                            'Temperature (degrees Celsius)': self.tempC})

            # if the next file-writing interval time is empty or in the past, update it
            if self.__nextFileTime is None or self.datetime.timestamp() > self.__nextFileTime:
                self.__nextFileTime = (
                  (
                    int(
                      self.datetime.timestamp()                        # timestamp in seconds
                      / self.config['temperature']['loggingFrequency'] # convert to number of intervals of length loggingFrequency
                    )                                                  # truncate to beginning of previous interval (past)
                  + 1)                                                 # advance by one time interval (future)
                  * self.config['temperature']['loggingFrequency']     # convert back to seconds/timestamp
                )

def main():

    root = Tk()
    temperature = Erl2Temperature(root)
    root.mainloop()

if __name__ == "__main__": main()

