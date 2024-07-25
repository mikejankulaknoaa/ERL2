# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from serial import Serial as ser
except:
    _hwLoaded = False

from multiprocessing import Process,Queue
from os import devnull
from re import split as re_split
from time import sleep
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Sensor import Erl2Sensor

# atlasScientific temperature sensor
class Erl2SerialTemp(Erl2Sensor):

    def __init__(self,
                 sensorType='temperature',
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 label=None,
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

        # private attributes specific to Erl2SerialTemp
        self.__port = self.erl2context['conf'][self.sensorType]['serialPort']
        self.__baud = self.erl2context['conf'][self.sensorType]['baudRate']
        self.__conn = None

        #print (f"{self.__class__.__name__}: Debug: __init__() port, baud is [{self.__port}][{self.__baud}]")

        # try connecting to the serial temperature sensor
        self.connect()

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2SerialTemp or a child class)
        if self.__class__.__name__ == 'Erl2SerialTemp':
            self.readSensor()

    def connect(self):

        # make sure the hardware library is present and the serial port is defined
        if not _hwLoaded or self.__port is None:
            self.__conn = None
            self.online = False

        else:
            # test if there's a serial device connected on this port
            # (waiting only 1 second for a reply)
            self.__conn = ser(self.__port, self.__baud, timeout=1)

            # try to turn off continuous input
            self.__conn.write(bytes('c,0\r','utf8'))

            # give it a moment to think about this one
            sleep(0.5)

            # discard any accumulated temp readings that were reported continuously
            self.__conn.reset_input_buffer()

            #print (f"{self.__class__.__name__}: Debug: connect(): sending 'status' to serial device")

            # check if 'status' is answered with a string beginning '?STATUS'
            self.__conn.write(bytes('status\r','utf8'))
            ans = self.__conn.read(7)

            if ans == b'?STATUS':

                # consume the rest of the reply, in case it messes things up
                limit=100
                while limit and self.__conn.read(1) != b'\r':
                    limit -= 1

                self.online = True

            else:
                self.__conn = None
                self.online = False

    def measure(self):

        # initialize the measurement result
        self.value = {}

        # try to connect again if serial device is missing
        if not self.online:
            self.connect()

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

        reply = {}

        # tell the serial device to take a measurement
        if self.__conn is not None:

            try:

                # reset buffer, then ask for a temperature reading
                self.__conn.reset_input_buffer()
                self.__conn.write(bytes('r\r','utf8'))
                ans = self.__conn.read(7)
                reply['temp.degC'] = float(re_split(b'[\r,]', ans)[0])

                # reset buffer, then ask for status message that includes voltage
                self.__conn.reset_input_buffer()
                self.__conn.write(bytes('status\r','utf8'))
                ans = self.__conn.read(18)
                reply['volts'] = float(re_split(b'[\r,]', ans)[2])

            except:
                pass

        q.put(reply)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2SerialTemp',font='Arial 30 bold').grid(row=0,column=0,columnspan=3)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0,columnspan=3)
    ttk.Label(statusFrame,text='Temperature last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')

    temp = Erl2SerialTemp(sensorType='temperature',
                          displayLocs=[{'parent':root,'row':1,'column':0}],
                          statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                          correctionLoc={'parent':root,'row':2,'column':0})

    root.mainloop()

if __name__ == "__main__": main()

