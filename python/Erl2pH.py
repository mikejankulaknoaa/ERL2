#! /usr/bin/python3

from pyrolib import PyroDevice
from Erl2Sensor import Erl2Sensor

# pyroscience pico-pH-sub sensor
class Erl2pH(Erl2Sensor):

    def __init__(self, parent, clones=[], port='/dev/ttyAMA1', baud=19200, tempSensor=None, tempParameter='temp.degC', parameter='pH', places=2, row=0, column=0, erl2conf=None):
        # call the Erl2Sensor class's constructor
        super().__init__(parent=parent, clones=clones, type='pH', parameter=parameter, places=places, row=row, column=column, erl2conf=erl2conf)

        # private attributes specific to Erl2pH
        self.__baud = baud

        # pH sensor needs to be told what the current temperature and salinity are
        self.__tempSensor = tempSensor
        self.__tempParameter = tempParameter
        self.__salinity = 35

        # set up the sensor for taking measurements
        self.__sensor = PyroDevice(port, baud)

        # start the loop to update the display widget every 1s
        self.readSensor()

    def measure(self):
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

def main():

    root = Tk()
    phsensor = Erl2pH(root)
    root.mainloop()

if __name__ == "__main__": main()

