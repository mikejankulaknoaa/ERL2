#! /usr/bin/python3

from pyrolib import PyroDevice
from Erl2Sensor import Erl2Sensor

# pyroscience pico-pH-sub sensor
class Erl2pH(Erl2Sensor):

    def __init__(self, parent, clones=[], port='/dev/ttyAMA1', baud=19200, parameter='pH', places=2, tempSensor=None, row=0, column=0, erl2conf=None):
        # call the Erl2Sensor class's constructor
        super().__init__(parent= parent, clones=clones, type='pH', row=row, column=column, erl2conf=erl2conf)

        # private attributes specific to Erl2pH
        self.__baud = baud
        self.__parameter = parameter
        self.__places = places

        # pH sensor needs to be told what the current temperature and salinity are
        self.__tempSensor = tempSensor
        self.__salinity = 35

        # set up the sensor for taking measurements
        self.__sensor = PyroDevice(port, baud)

        # override the parent class's (public) 'value' attribute
        self.value = {}

        # start the loop to update the display widget every 1s
        self.readSensor()

    def measure(self):
        # tell the pico-H what the current temperature and salnity are
        self.__sensor[1].settings['temp'] = self.__tempSensor.value['tempC']
        self.__sensor[1].settings['salinity'] = self.__salinity

        # tell the pico-pH to take a measurement
        m = self.__sensor.measure()

        # this sensor has only one channel: channel 1
        self.value = m[1]

        # return the measurement result as a dict
        # (key values will be used as headers in the output csv)
        return m[1]

    def updateDisplays(self, widgets):
        # loop through all placements of this sensor's displays
        for w in widgets:

            # update the display
            w.config(text=f"{float(round(self.value[self.__parameter],self.__places)):.{self.__places}f}")

def main():

    root = Tk()
    phsensor = Erl2pH(root)
    root.mainloop()

if __name__ == "__main__": main()

