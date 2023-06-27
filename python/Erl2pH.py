#! /usr/bin/python3

from pyrolib import PyroDevice
from Erl2Sensor import Erl2Sensor

# pyroscience pico-pH-sub sensor
class Erl2pH(Erl2Sensor):

    def __init__(self,
                 displayLocs=[],
                 port='/dev/ttyAMA1',
                 baud=19200,
                 tempSensor=None,
                 tempParameter='temp.degC',
                 parameter='pH',
                 places=2,
                 erl2conf=None,
                 img=None):

        # call the Erl2Sensor class's constructor
        super().__init__(type='pH',
                         displayLocs=displayLocs,
                         parameter=parameter,
                         places=places,
                         erl2conf=erl2conf,
                         img=img)

        # track if the pico-pH is installed correctly
        self.__installed = False

        # private attributes specific to Erl2pH
        self.__baud = baud

        # pH sensor needs to be told what the current temperature and salinity are
        self.__tempSensor = tempSensor
        self.__tempParameter = tempParameter
        self.__salinity = 35

        # try connecting to the pH sensor
        self.connect()

        # start the loop to update the display widgets every 1s
        self.readSensor()

    def connect(self):

        self.__installed = False

        # set up the sensor for taking measurements
        try:
            self.__sensor = PyroDevice(port, baud)
            self.__installed = True
        except:
            pass

    def measure(self):

        # try to connect again if pico-pH is missing
        if not self.__installed:
            self.connect()

        # proceed only if we are connected
        if self.__installed:
            # tell the pico-H what the current temperature and salnity are
            self.__sensor[1].settings['temp'] = self.__tempSensor.value[self.__tempParameter]
            self.__sensor[1].settings['salinity'] = self.__salinity

            # tell the pico-pH to take a measurement
            m = self.__sensor.measure()

            # this sensor has only one channel: channel 1
            self.value = m[1]

            # return the measurement result as a dict
            # (key values will be used as headers in the output csv)
            return m[1]

        else:
            self.value = {'pH':0., 'pressure':0.}
            return self.value

def main():

    root = Tk()
    phsensor = Erl2pH(root)
    root.mainloop()

if __name__ == "__main__": main()

