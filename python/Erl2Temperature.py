#! /usr/bin/python3

import megaind as ind
from Erl2Sensor import Erl2Sensor

# ProSense Pt100 temperature transmitter XTP25N-100-0100C
class Erl2Temperature(Erl2Sensor):

    def __init__(self, parent, clones=[], stack=0, channel=1, parameter='temp.degC', places=1, row=0, column=0, erl2conf=None):
        # call the Erl2Sensor class's constructor
        super().__init__(parent=parent, clones=clones, type='temperature', parameter=parameter, places=places, row=row, column=column, erl2conf=erl2conf)

        # private attributes specific to Erl2Temperature
        self.__stack = stack
        self.__channel = channel

        # start the loop to update the display widget every 1s
        self.readSensor()

    def measure(self):
        # reinitialize self.value
        self.value = {}

        # milliAmps are read from the input channel
        self.value['temp.mA'] = ind.get4_20In(self.__stack, self.__channel)

        # convert from 4-20 mA to 0-100 degC
        self.value['temp.degC'] = (self.value['temp.mA'] - 4.) * 100. / 16.

        # return the measurement result as a dict
        # (key values will be used as headers in the output csv)
        return self.value

def main():

    root = Tk()
    temperature = Erl2Temperature(root)
    root.mainloop()

if __name__ == "__main__": main()

