#! /usr/bin/python3

import megaind as ind
from Erl2Sensor import Erl2Sensor

# ProSense Pt100 temperature transmitter XTP25N-100-0100C
class Erl2Temperature(Erl2Sensor):

    def __init__(self, parent, clones=[], stack=0, channel=1, units='c', places=1, row=0, column=0, erl2conf=None):
        # call the Erl2Sensor class's constructor
        super().__init__(parent=parent, clones=clones, type='temperature', row=row, column=column, erl2conf=erl2conf)

        # private attributes specific to Erl2Temperature
        self.__stack = stack
        self.__channel = channel
        self.__units = units
        self.__places = places

        # override the parent class's (public) 'value' attribute
        self.value = {}
        self.value['tempMa'] = None
        self.value['tempC'] = None
        self.value['tempF'] = None

        # start the loop to update the display widget every 1s
        self.readSensor()

    def measure(self):
        # milliAmps are read from the input channel
        self.value['tempMa'] = ind.get4_20In(self.__stack, self.__channel)

        # convert from 4-20 mA to 0-100 degC
        self.value['tempC'] = (self.value['tempMa'] - 4.) * 100. / 16.

        # convert degC to degF
        self.value['tempF'] = self.value['tempC'] * 9. / 5. + 32.

        # return the measurement result as a dict
        # (key values will be used as headers in the output csv)
        return {'milliAmps': self.value['tempMa'],
                'Temperature (degrees Celsius)': self.value['tempC']}

    def updateDisplays(self, widgets):
        # loop through all placements of this sensor's displays
        for w in widgets:

            # update the display (default is degC)
            if self.__units == 'f':
                w.config(text=f"{float(round(self.value['tempF'],self.__places)):.{self.__places}f}")
            elif self.__units == 'ma':
                w.config(text=f"{float(round(self.value['tempMa'],self.__places)):.{self.__places}f}")
            else:
                w.config(text=f"{float(round(self.value['tempC'],self.__places)):.{self.__places}f}")

def main():

    root = Tk()
    temperature = Erl2Temperature(root)
    root.mainloop()

if __name__ == "__main__": main()

