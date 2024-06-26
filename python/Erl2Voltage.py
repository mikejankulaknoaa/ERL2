# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from board import SCL, SDA
except:
    _hwLoaded = False

from adafruit_ina260 import INA260
from busio import I2C
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Sensor import Erl2Sensor

# coded to support adafruit INA260 current/voltage/power sensor

class Erl2Voltage(Erl2Sensor):

    def __init__(self,
                 sensorType='voltage',
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
        assert(_hwLoaded or self.erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # connection details for this sensor
        self.i2c = None
        self.ina260 = None

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Voltage or a child class)
        if self.__class__.__name__ == 'Erl2Voltage':
            self.readSensor()

    def measure(self):

        # initialize the measurement result
        self.value = {}

        # ignore missing hardware libraries on windows
        if _hwLoaded:

            # if the sensor isn't configured yet, try to do so now
            if self.ina260 is None:
                self.setupSensor()

            # assuming the setup worked okay, proceed
            if self.ina260 is not None:
                try:
                    self.value['current'] = self.ina260.current
                    self.value['voltage'] = self.ina260.voltage
                    self.value['power'] = self.ina260.power
                except:
                    pass

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

    def setupSensor(self):

        try:
            self.i2c = I2C(SCL, SDA)
            self.ina260 = INA260(self.i2c)
        except:
            self.i2c = None
            self.ina260 = None

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Voltage',font='Arial 30 bold').grid(row=0,column=0,columnspan=4)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0,columnspan=4)
    ttk.Label(statusFrame,text='Voltage last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')

    voltage = Erl2Voltage(sensorType='voltage',
                          displayLocs=[{'parent':root,'row':1,'column':1}],
                          statusLocs=[{'parent':statusFrame,'row':1,'column':1}])

    root.mainloop()

if __name__ == "__main__": main()

