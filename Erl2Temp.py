#! /usr/bin/python3

from tkinter import *
from tkinter import ttk
import megaind as ind

# ProSense Pt100 temperature transmitter XTP25N-100-0100C
class Erl2Temp():

    def __init__(self, parent, stack=0, channel=1, units='c', places=1):
        self.__parent = parent
        self.__stack = stack
        self.__channel = channel
        self.__units = units
        self.__places = places

        # these attributes can be accessed outside the class
        self.tempMa = None
        self.tempC = None
        self.tempF = None

        # stylistic stuff
        #s = ttk.Style()
        #s.configure('Erl2Temp.TLabel',foreground='1C4587', font='Arial 40 bold')

        self.__frame = ttk.Frame(self.__parent, padding='2 2', relief='solid', borderwidth=1)
        self.__frame.grid(column=1, row=1, padx='2', pady='2', sticky='ne')

        # a Label to show the current temperature
        self.__tempDisplay = ttk.Label(self.__frame, text='0.0', font='Arial 40 bold', foreground='#1C4587')
        #self.__tempDisplay.configure(style='Erl2Temp.TLabel')
        self.__tempDisplay.grid(column=1, row=1, sticky='nwse')
        self.__frame.columnconfigure(1,weight=1)
        self.__frame.rowconfigure(1,weight=1)

        # start the loop to update the temperature every 1s
        self.readTemp()


    def readTemp(self):
        # milliAmps are read from the input channel
        self.tempMa = ind.get4_20In(self.__stack, self.__channel)

        # convert from 4-20 mA to 0-100 degC
        self.tempC = self.tempMa * 100. / 16. - 25.

        # convert degC to degF
        self.tempF = self.tempC * 9. / 5. + 32.

        # update the display
        if self.__units == 'f':
            self.__tempDisplay.config(text=f'{float(round(self.tempF,self.__places)):.{self.__places}f}')
        elif self.__units == 'ma':
            self.__tempDisplay.config(text=f'{float(round(self.tempMa,self.__places)):.{self.__places}f}')
        else:
            self.__tempDisplay.config(text=f'{float(round(self.tempC,self.__places)):.{self.__places}f}')

        # update again after 1s
        self.__tempDisplay.after(1000, self.readTemp)

def main():

    root = Tk()
    temp = Erl2Temp(root)
    root.mainloop()

if __name__ == "__main__": main()

