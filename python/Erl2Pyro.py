# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from pyrolib import PyroDevice
    from serial import Serial as ser
except:
    _hwLoaded = False

from contextlib import contextmanager,redirect_stderr,redirect_stdout
from multiprocessing import Process,Queue
from os import devnull
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Input import Erl2Input
from Erl2Sensor import Erl2Sensor

# pyroscience pico-pH and pico-o2 sensors
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
                 sensorType='generic', # pico-pH uses 'pH', pico-o2 uses 'uM' (microMoles per Liter)
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 label=None,
                 tempSensor=None,
                 erl2context={}):

        # call the Erl2Sensor class's constructor
        super().__init__(sensorType=sensorType,
                         displayLocs=displayLocs,
                         statusLocs=statusLocs,
                         correctionLoc=correctionLoc,
                         label=label,
                         erl2context=erl2context)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        #print (f"{self.__class__.__name__}: Debug: platform is [{self.erl2context['conf']['system']['platform']}]")
        assert(_hwLoaded or self.erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # private attributes specific to Erl2Pyro
        self.__port = self.erl2context['conf'][self.sensorType]['serialPort']
        self.__baud = self.erl2context['conf'][self.sensorType]['baudRate']
        self.__device = None

        # PyroDevice needs to be told what the current temperature and salinity are
        self.__tempSensor = tempSensor
        self.__tempParameter = self.erl2context['conf']['temperature']['displayParameter']
        self.__salinity = 35

        # try connecting to the PyroDevice
        self.connect()

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Pyro or a child class)
        if self.__class__.__name__ == 'Erl2Pyro':
            self.readSensor()

    def connect(self):

        # before doing anything, try to verify that there's a PyroDevice connected
        if self.testSerial():

            # ignore missing hardware libraries on windows
            if _hwLoaded:
                # set up the sensor for taking measurements
                try:
                    # prevent the pyrolibs code from spamming stdout
                    #with self.suppress_stdout():
                        self.__device = PyroDevice(self.__port, self.__baud)
                        #if not self.online:
                        #    print (f"{self.__class__.__name__}: Debug: connect(): PyroDevice() succeeded, [{self.sensorType}] sensor going online")
                        self.online = True

                except Exception as e:
                    #if self.online:
                    #    print (f"{self.__class__.__name__}: Debug: connect(): PyroDevice() failed, [{self.sensorType}] sensor going offline [{e}]")
                    self.online = False

            else:
                self.online = False

        else:
            #if self.online:
            #    print (f"{self.__class__.__name__}: Debug: connect(): testSerial() failed, [{self.sensorType}] sensor going offline")
            self.online = False

    def measure(self):

        # initialize the measurement result
        self.value = {}

        # try to connect again if PyroDevice is missing
        if not self.online:
            self.connect()

        # another problem would be if the temperature sensor were offline
        if not self.__tempSensor.online:
            #if self.online:
            #    print (f"{self.__class__.__name__}: Debug: measure(): tempSensor is offline, [{self.sensorType}] sensor going offline")
            self.online = False

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
        #if self.online != (self.value != {}):
        #    print (f"{self.__class__.__name__}: Debug: measure(): measurement result triggers [{self.sensorType}] sensor to go {'off' if self.online else 'on'}line")
        self.online = (self.value != {})

        # add Timestamps to measurement record
        t, m = self.getTimestamp()

        # produce the final measurement dict with timestamps and values
        self.value = {**m, **self.value}

        # remember timestamp of last valid measurement
        if self.online:
            self.lastValid = t

        # apply the corrective offset
        self.applyOffset(self.value, updateRaw=True)

        # return timestamp, measurement and status
        return t, self.value, self.online

    def measureWrapper(self, q):

        # prevent the pyrolibs code from spamming stdout
        with self.suppress_stdout():

            # tell the PyroDevice what the current temperature and salinity are
            if self.__tempSensor.online:
                self.__device[1].settings['temp'] = self.__tempSensor.value[self.__tempParameter]
            self.__device[1].settings['salinity'] = self.__salinity

            # tell the PyroDevice to take a measurement
            m = self.__device.measure()

            # this sensor has only one channel: channel 1
            # (return this value -- a python dict -- via the process queue)
            q.put(m[1])

    def testSerial(self):

        # silently fail if the hardware library is missing
        if not _hwLoaded:
            return False

        # silently fail if the serial port isn't defined
        if self.__port is None:
            return False

        # test if there's a PyroDevice connected on this port
        # (waiting only 1 second for a reply)
        conn = ser(self.__port, self.__baud, timeout=1)
        conn.write(bytes('#VERS\r','utf8'))
        ans = conn.read(5)

        if ans == b'#VERS':

            # consume the rest of the reply, in case it messes pyrolib up
            limit=100
            while limit and conn.read(1) != b'\r':
                limit -= 1

            # success!
            return True

        # otherwise, bad news
        return False

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Pyro',font='Arial 30 bold').grid(row=0,column=0,columnspan=3)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0,columnspan=3)
    ttk.Label(statusFrame,text='Temperature last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nse')
    ttk.Label(statusFrame,text='pH last read:',font='Arial 14 bold',justify='right').grid(row=1,column=0,sticky='nse')
    ttk.Label(statusFrame,text='DO last read:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nse')

    temperature = Erl2Input(sensorType='temperature',
                            displayLocs=[{'parent':root,'row':1,'column':0}],
                            statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                            correctionLoc={'parent':root,'row':2,'column':0})
    ph = Erl2Pyro(sensorType='pH',
                  displayLocs=[{'parent':root,'row':1,'column':1}],
                  statusLocs=[{'parent':statusFrame,'row':1,'column':1}],
                  correctionLoc={'parent':root,'row':2,'column':1},
                  tempSensor=temperature)
    o2 = Erl2Pyro(sensorType='DO',
                  displayLocs=[{'parent':root,'row':1,'column':2}],
                  statusLocs=[{'parent':statusFrame,'row':2,'column':1}],
                  correctionLoc={'parent':root,'row':2,'column':2},
                  tempSensor=temperature)

    root.mainloop()

if __name__ == "__main__": main()

