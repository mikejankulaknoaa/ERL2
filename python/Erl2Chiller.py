#! /usr/bin/python3

from megaind import setOdPWM
import tkinter as tk
from tkinter import ttk
from Erl2Toggle import Erl2Toggle

class Erl2Chiller(Erl2Toggle):

    def __init__(self,
                 displayLocs=[],
                 buttonLocs=[],
                 displayImages=['button-grey-30.png','button-blue-30.png'],
                 buttonImages=['radio-off-blue-30.png','radio-on-blue-30.png'],
                 label='Chiller',
                 stack=0,
                 channel=None,
                 erl2context={}):

        # call the Erl2Toggle class's constructor
        super().__init__(type='chiller',
                         displayLocs=displayLocs,
                         buttonLocs=buttonLocs,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2context=erl2context)

        # private attributes specific to Erl2Chiller
        self.__stack = stack
        self.__channel = channel

        # the default output channel for the ERL2 chiller solenoid is 1
        if self.__channel is None:
            self.__channel = 1

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Chiller or a child class)
        if self.__class__.__name__ == 'Erl2Chiller':
            self.updateLog()

    def changeHardwareState(self):

        # apply the new state to the chiller solenoid hardware
        #print (f"{self.__class__.__name__}: Debug: changing to state [{self.state}] on channel [{self.__channel}]")

        if self.state:
            # turn on chiller -- set to 100%
            setOdPWM(self.__stack,self.__channel,100)
        else:
            # turn off chiller -- set to 0%
            setOdPWM(self.__stack,self.__channel,0)

def main():

    root = tk.Tk()
    chiller = Erl2Chiller(displayLocs=[{'parent':root,'row':0,'column':0}],
                          buttonLocs=[{'parent':root,'row':1,'column':0}])
    chiller.setActive()
    root.mainloop()

if __name__ == "__main__": main()

