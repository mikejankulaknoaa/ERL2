#! /usr/bin/python3

from tkinter import *
from tkinter import ttk
from time import strftime
from Erl2Config import Erl2Config

# clock/calendar widget adapted from an example found at
# https://www.geeksforgeeks.org/python-create-a-digital-clock-using-tkinter/#

class Erl2Clock():

    def __init__(self, parent, clockType='oneline', withSeconds=False, erl2conf=None, img=None):

        self.__parent = parent
        self.__clockType = clockType
        self.__withSeconds = withSeconds
        self.__erl2conf = erl2conf

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # create the clock's base frame as a child of its parent
        self.__frame = ttk.Frame(self.__parent, padding='2 2', relief='solid', borderwidth=1)
        self.__frame.grid(row=0, column=0, padx='5', pady='2', sticky='ne')

        # add the Label widgets for time and date
        self.__clockTime = ttk.Label(self.__frame, text='14:20', font='Arial 16 bold')
        self.__clockDate = ttk.Label(self.__frame, text='1.16.23', font='Arial 12')

        # different positioning depending on clock type
        if self.__clockType == 'oneline':
            self.__clockTime.grid(row=0, column=0, sticky='s')
            self.__clockDate.grid(row=0, column=1, sticky='s')
            self.__frame.rowconfigure(0,weight=1)
            self.__frame.columnconfigure(0,weight=1)
            self.__frame.columnconfigure(1,weight=1)
        else:
            self.__clockTime.grid(row=0, column=0, sticky='n')
            self.__clockDate.grid(row=1, column=0, sticky='s')
            self.__frame.rowconfigure(0,weight=1)
            self.__frame.rowconfigure(1,weight=1)
            self.__frame.columnconfigure(0,weight=1)

        # start the loop to update the clock every 1s
        self.myClock()

    # this method runs every second to update the clock readout
    def myClock(self):
        # I am zero-padding the hour, minute and day-of-month, but not the month
        if self.__withSeconds:
            clockTime = strftime('%H:%M:%S')
        else:
            clockTime = strftime('%H:%M')
        clockDate = strftime('%-m.%d.%y')
        self.__clockTime.config(text=clockTime)
        self.__clockDate.config(text=clockDate)

        # update the clock display again after 1s
        self.__clockDate.after(1000, self.myClock)

def main():

    root = Tk()
    clock = Erl2Clock(root)
    root.mainloop()

if __name__ == "__main__": main()

