import tkinter as tk
from tkinter import ttk
from datetime import datetime as dt
from Erl2Config import Erl2Config
from Erl2Useful import locDefaults

# clock/calendar widget adapted from an example found at
# https://www.geeksforgeeks.org/python-create-a-digital-clock-using-tkinter/#

class Erl2Clock():

    def __init__(self, clockLoc={}, erl2context={}):

        #self.__clockLoc = clockLoc
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # return immediately if there's no parent frame specified
        if 'parent' not in clockLoc:
            return

        # location defaults for clock module
        modDefaults = {'relief'      : 'flat',
                       'borderwidth' : 0,
                       'padx'        : '5 5',
                       'pady'        : '3 3',
                       'sticky'      : 'ne',
                       }
        loc = locDefaults(loc=clockLoc, modDefaults=modDefaults)

        # create the clock's base frame as a child of its parent
        self.__frame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.__frame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                          padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])

        # add the Label widgets for time and date
        self.__clockTime = ttk.Label(self.__frame, text='14:20', font='Arial 16 bold')
        self.__clockDate = ttk.Label(self.__frame, text='1.16.23', font='Arial 12')

        # different positioning depending on clock type
        if self.erl2context['conf']['system']['clockTwoLines']:
            self.__clockTime.grid(row=0, column=0, sticky='n')
            self.__clockDate.grid(row=1, column=0, sticky='s')
            self.__frame.rowconfigure(0,weight=1)
            self.__frame.rowconfigure(1,weight=1)
            self.__frame.columnconfigure(0,weight=1)
        else:
            self.__clockTime.grid(row=0, column=0, padx=2, sticky='s')
            self.__clockDate.grid(row=0, column=1, padx=2, sticky='s')
            self.__frame.rowconfigure(0,weight=1)
            self.__frame.columnconfigure(0,weight=1)
            self.__frame.columnconfigure(1,weight=1)

        # start the loop to update the clock every 1s
        self.myClock()

    # this method runs every second to update the clock readout
    def myClock(self):

        # the current time
        clock = dt.now()

        # I am zero-padding the hour, minute and day-of-month, but not the month
        if self.erl2context['conf']['system']['hideClockSeconds']:
            clockTime = clock.strftime('%H:%M')
        else:
            clockTime = clock.strftime('%H:%M:%S')
        clockDate = clock.strftime('%m.%d.%y').lstrip('0')
        self.__clockTime.config(text=clockTime)
        self.__clockDate.config(text=clockDate)

        # update the clock display again after 1s
        self.__clockDate.after(1000, self.myClock)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Clock',font='Arial 30 bold').grid(row=0,column=0)
    clock = Erl2Clock({'parent':root,'row':1,'column':0})
    root.mainloop()

if __name__ == "__main__": main()

