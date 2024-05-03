# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from megaind import setOdPWM
except:
    _hwLoaded = False

import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Control import Erl2Control
from Erl2Useful import locDefaults

class Erl2Chiller(Erl2Control):

    def __init__(self,
                 displayLocs=[],
                 buttonLoc={},
                 displayImages=['button-grey-30.png','button-blue-30.png'],
                 buttonImages=['radio-off-blue-30.png','radio-on-blue-30.png'],
                 label='Chiller',
                 erl2context={}):

        # controlType will be 'chiller'
        controlType = 'chiller'

        # hack up the displayLocs with chiller-specific defaults before calling parent __init__
        chillerLocs = []
        for loc in displayLocs:
            chillerLocs.append(locDefaults(loc=loc,modDefaults={'relief':'flat','borderwidth':0,'padx':'2','pady':'2'}))

        # read in the system configuration file if needed
        if 'conf' not in erl2context:
            erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # read these useful parameters from Erl2Config
        self.__stackLevel = erl2context['conf'][controlType]['stackLevel']
        self.__outputPwmChannel = erl2context['conf'][controlType]['outputPwmChannel']

        # call the Erl2Control class's constructor
        super().__init__(controlType=controlType,
                         widgetType='button',
                         widgetLoc=buttonLoc,
                         displayLocs=chillerLocs,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2context=erl2context)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Chiller or a child class)
        if self.__class__.__name__ == 'Erl2Chiller':
            self.updateLog()

    def changeHardwareSetting(self):

        # apply the new setting to the chiller solenoid hardware
        #print (f"{self.__class__.__name__}: Debug: changing chiller to setting [{int(self.setting)}] on Open-Drain / PWM output channel [{self.__outputPwmChannel}]")

        # ignore missing hardware libraries on windows
        if _hwLoaded:
            if self.setting:
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

