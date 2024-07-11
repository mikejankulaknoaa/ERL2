# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from megaind import setOdPWM, set0_10Out
except:
    _hwLoaded = False

import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Control import Erl2Control
from Erl2Useful import locDefaults

class Erl2MegaindOutput(Erl2Control):

    def __init__(self,
                 controlType='generic',
                 controlColor=None,
                 displayLocs=[],
                 buttonLoc={},
                 displayImages=['button-grey-30.png','button-blue-30.png'],
                 buttonImages=['radio-off-blue-30.png','radio-on-blue-30.png'],
                 erl2context={}):

        # label is just capitalized controlType
        label = controlType.capitalize()

        # hack up the displayLocs with module-specific defaults before calling parent __init__
        modDisplayLocs = []
        for loc in displayLocs:
            modDisplayLocs.append(locDefaults(loc=loc,modDefaults={'relief':'flat','borderwidth':0,'padx':'2','pady':'2'}))

        # hack up images with different color, if supplied
        modDisplayImages = displayImages.copy()
        modButtonImages = buttonImages.copy()
        if controlColor is not None and controlColor != 'blue':
            modDisplayImages = [ x.replace('blue', controlColor) for x in modDisplayImages ]
            modButtonImages = [ x.replace('blue', controlColor) for x in modButtonImages ]

        # read in the system configuration file if needed
        if 'conf' not in erl2context:
            erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # read these useful parameters from Erl2Config
        self.__channelType = erl2context['conf'][controlType]['channelType']
        self.__stackLevel = erl2context['conf'][controlType]['stackLevel']
        self.__outputChannel = erl2context['conf'][controlType]['outputChannel']

        # call the Erl2Control class's constructor
        super().__init__(controlType=controlType,
                         widgetType='button',
                         widgetLoc=buttonLoc,
                         displayLocs=modDisplayLocs,
                         displayImages=modDisplayImages,
                         buttonImages=modButtonImages,
                         label=label,
                         erl2context=erl2context)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2MegaindOutput or a child class)
        if self.__class__.__name__ == 'Erl2MegaindOutput':
            self.updateLog()

    def changeHardwareSetting(self):

        # apply the new setting to the output channel
        #print (f"{self.__class__.__name__}: Debug: changing [{self.controlType}] to setting [{int(self.setting)}] on Open-Drain / PWM output channel [{self.__outputChannel}]")

        # ignore missing hardware libraries on windows
        if _hwLoaded:

            # if this is an Open-drain Pulse-Width Modulation (setOdPWM) output
            if self.__channelType == 'pwm':
                if self.setting:
                    # turn on output -- set to 100%
                    #print (f"{self.__class__.__name__}: Debug: changeHardwareSetting: setOdPWM({self.__stackLevel},{self.__outputChannel},100)")
                    setOdPWM(self.__stackLevel,self.__outputChannel,100)
                else:
                    # turn off output -- set to 0%
                    #print (f"{self.__class__.__name__}: Debug: changeHardwareSetting: setOdPWM({self.__stackLevel},{self.__outputChannel},0)")
                    setOdPWM(self.__stackLevel,self.__outputChannel,0)

            # if this is a 0V-10V (set0_10Out) output
            elif self.__channelType == '10v':
                if self.setting:
                    # turn on output -- set to 10V
                    #print (f"{self.__class__.__name__}: Debug: changeHardwareSetting: set0_10Out({self.__stackLevel},{self.__outputChannel},10)")
                    set0_10Out(self.__stackLevel,self.__outputChannel,10)
                else:
                    # turn off output -- set to 0V
                    #print (f"{self.__class__.__name__}: Debug: changeHardwareSetting: set0_10Out({self.__stackLevel},{self.__outputChannel},0)")
                    set0_10Out(self.__stackLevel,self.__outputChannel,0)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2MegaindOutput',font='Arial 30 bold').grid(row=0,column=0)
    chiller = Erl2MegaindOutput(controlType='chiller',
                                controlColor='blue',
                                displayLocs=[{'parent':root,'row':1,'column':0}],
                                buttonLoc={'parent':root,'row':2,'column':0})
    chiller.setActive()
    root.mainloop()

if __name__ == "__main__": main()

