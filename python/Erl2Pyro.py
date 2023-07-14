#! /usr/bin/python3

from contextlib import contextmanager,redirect_stderr,redirect_stdout
from multiprocessing import Process,Queue
from os import devnull
from pyrolib import PyroDevice
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Sensor import Erl2Sensor
from Erl2Temperature import Erl2Temperature

# pyroscience pico-pH-sub and pico-o2-sub sensors
class Erl2Pyro(Erl2Sensor):

    # note: adapted this redirection code from something found at
    # https://stackoverflow.com/questions/11130156/suppress-stdout-stderr-print-from-python-functions

    @contextmanager
    def suppress_stdout(self):
        """A context manager that redirects stdout to devnull"""
        with open(devnull, 'w') as fnull:
            with redirect_stdout(fnull) as out:
                yield (out)

    def __init__(self,
                 sensorType='unknown', # pico-sub-pH uses 'pH', pico-o2-sub uses 'uM' (microMoles per Liter)
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 tempSensor=None,
                 erl2context={}):

        # call the Erl2Sensor class's constructor
        super().__init__(sensorType=sensorType,
                         displayLocs=displayLocs,
                         statusLocs=statusLocs,
                         correctionLoc=correctionLoc,
                         erl2context=erl2context)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # private attributes specific to Erl2Pyro
        self.__port = self.erl2context['conf'][self.sensorType]['serialPort']
        self.__baud = self.erl2context['conf'][self.sensorType]['baudRate']

        # pH sensor needs to be told what the current temperature and salinity are
        self.__tempSensor = tempSensor
        self.__tempParameter = self.erl2context['conf']['temperature']['displayParameter']
        self.__salinity = 35

        # try connecting to the pH sensor
        self.connect()

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Pyro or a child class)
        if self.__class__.__name__ == 'Erl2Pyro':
            self.readSensor()

    def connect(self):

        # set up the sensor for taking measurements
        try:
            # prevent the pyrolibs code from spamming stdout
            with self.suppress_stdout():
                self.__sensor = PyroDevice(self.__port, self.__baud)
                self.online = True
                #print (f"{self.__class__.__name__}: Debug: PyroDevice connect() succeeded, pH sensor is online")

        except Exception as e:
            self.online = False
            #print (f"{self.__class__.__name__}: Debug: PyroDevice connect() failed, pH sensor is offline [{e}]")

    def measure(self):

        # initialize the measurement result
        self.value = {}

        # try to connect again if pico-pH is missing
        if not self.online:
            self.connect()

        # another problem would be if the temperature sensor were offline
        if not self.__tempSensor.online:
            self.online = False
            #print (f"{self.__class__.__name__}: Debug: setting pH sensor offline because temp sensor is offline")

        # proceed only if we are connected
        if self.online:

            # fork a new process for the measurement, in case it never finishes
            q = Queue()
            p = Process(target=self.measureWrapper, args=(q,))
            p.start()

            # give up after waiting 5 seconds
            p.join(5)

            # kill the process if it never completed
            if p.is_alive():
                p.kill()

            # otherwise get the return value from the process queue
            else:
                self.value = q.get()

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

    def measureWrapper(self, q):

        # prevent the pyrolibs code from spamming stdout
        with self.suppress_stdout():

            # tell the pico-pH or pico-o2 what the current temperature and salinity are
            if self.__tempSensor.online:
                self.__sensor[1].settings['temp'] = self.__tempSensor.value[self.__tempParameter]
            self.__sensor[1].settings['salinity'] = self.__salinity

            # tell the pico-pH to take a measurement
            m = self.__sensor.measure()

            # this sensor has only one channel: channel 1
            # (return this value -- a python dict -- via the process queue)
            q.put(m[1])

def main():

    root = tk.Tk()
    temperature = Erl2Temperature(displayLocs=[{'parent':root,'row':0,'column':0}],
                                  statusLocs=[{'parent':root,'row':1,'column':0}],
                                  correctionLoc={'parent':root,'row':2,'column':0})
    ph = Erl2Pyro(sensorType='pH',
                  displayLocs=[{'parent':root,'row':0,'column':1}],
                  statusLocs=[{'parent':root,'row':1,'column':1}],
                  correctionLoc={'parent':root,'row':2,'column':1},
                  tempSensor=temperature)

    o2 = Erl2Pyro(sensorType='DO',
                  displayLocs=[{'parent':root,'row':0,'column':2}],
                  statusLocs=[{'parent':root,'row':1,'column':2}],
                  correctionLoc={'parent':root,'row':2,'column':2},
                  tempSensor=temperature)

    root.mainloop()

if __name__ == "__main__": main()

