#! /usr/bin/python3

# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from megaind import setOdPWM
except:
    _hwLoaded = False

import tkinter as tk
from tkinter import ttk
from Erl2Toggle import Erl2Toggle

class Erl2Chiller(Erl2Toggle):

    def __init__(self,
                 displayLocs=[],
                 buttonLoc={},
                 displayImages=['button-grey-30.png','button-blue-30.png'],
                 buttonImages=['radio-off-blue-30.png','radio-on-blue-30.png'],
                 label='Chiller',
                 erl2context={}):

        # call the Erl2Toggle class's constructor
        super().__init__(controlType='chiller',
                         displayLocs=displayLocs,
                         buttonLoc=buttonLoc,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2context=erl2context)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # force an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or self.erl2context['conf']['system']['platform'] == 'win32')

        # read these useful parameters from Erl2Config
        self.__stackLevel = self.erl2context['conf'][self.controlType]['stackLevel']
        self.__outputPwmChannel = self.erl2context['conf'][self.controlType]['outputPwmChannel']

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Chiller or a child class)
        if self.__class__.__name__ == 'Erl2Chiller':
            self.updateLog()

    def changeHardwareState(self):

        # apply the new state to the chiller solenoid hardware
        #print (f"{self.__class__.__name__}: Debug: changing to state [{self.state}] on Open-Drain / PWM output channel [{self.__outputPwmChannel}]")

        # ignore missing hardware libraries on windows
        if _hwLoaded:
            if self.state:
                # turn on chiller -- set to 100%
                setOdPWM(self.__stackLevel,self.__outputPwmChannel,100)
            else:
                # turn off chiller -- set to 0%
                setOdPWM(self.__stackLevel,self.__outputPwmChannel,0)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Chiller',font='Arial 30 bold').grid(row=0,column=0)
    chiller = Erl2Chiller(displayLocs=[{'parent':root,'row':1,'column':0}],
                          buttonLoc={'parent':root,'row':2,'column':0})
    chiller.setActive()
    root.mainloop()

if __name__ == "__main__": main()

