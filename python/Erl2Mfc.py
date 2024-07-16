# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from megaind import set0_10Out
except:
    _hwLoaded = False

from datetime import datetime as dt
from datetime import timezone as tz
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Control import Erl2Control
from Erl2Input import Erl2Input

# MFC = Mass Flow Controllers (gas rates for Air, CO2, N2)

class Erl2Mfc(Erl2Control):

    def __init__(self,
                 controlType='generic',
                 displayLocs=[],
                 entryLoc={},
                 label=None,
                 erl2context={}):

        # if no label supplied, try to deduce from MFC control type
        if label is None:
            if controlType == 'mfc.air':
                label = 'Air'
            elif controlType == 'mfc.co2':
                label = u'CO\u2082'
            elif controlType == 'mfc.n2':
                label = u'N\u2082'
            else:
                label = controlType[4:]

        # read in the system configuration file if needed
        if 'conf' not in erl2context:
            erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # read these useful parameters from Erl2Config
        self.__stackLevel = erl2context['conf'][controlType]['stackLevel']
        self.__outputChannel = erl2context['conf'][controlType]['outputChannel']

        # call the Erl2Control class's constructor
        super().__init__(controlType=controlType,
                         widgetType='entry',
                         widgetLoc=entryLoc,
                         displayLocs=displayLocs,
                         label=label,
                         erl2context=erl2context)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Mfc or a child class)
        if self.__class__.__name__ == 'Erl2Mfc':
            self.updateLog()

    def changeHardwareSetting(self):

        # calculate the Vdc that corresponds to the current setting
        volts = (self.setting - self.validRange[0]) / (self.validRange[1] - self.validRange[0]) * 5.

        # don't exceed the range of 0 - 5 V
        if volts > 5.:
            volts = 5.
        elif volts < 0.:
            volts = 0.

        #print (f"{self.__class__.__name__}: Debug: changeHardwareSetting({self.controlType}): stack/channel is [{self.__stackLevel}]/[{self.__outputChannel}], setting is [{self.setting}], volts is [{volts}]")

        # ignore missing hardware libraries on windows
        if _hwLoaded:
            # apply this voltage to the output channel
            set0_10Out(self.__stackLevel,self.__outputChannel,volts)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Mfc',font='Arial 30 bold').grid(row=0,column=0,columnspan=3)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=4,column=0,columnspan=3)
    ttk.Label(statusFrame,text='Air MFC last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')
    ttk.Label(statusFrame,text='CO2 MFC last read:',font='Arial 14 bold',justify='right').grid(row=1,column=0,sticky='nes')
    ttk.Label(statusFrame,text='N2 MFC last read:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nes')

    sensorMfcAir = Erl2Input(sensorType='mfc.air',
                             displayLocs=[{'parent':root,'row':1,'column':0}],
                             statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                             label='Air'
                             )
    sensorMfcCO2 = Erl2Input(sensorType='mfc.co2',
                             displayLocs=[{'parent':root,'row':1,'column':1}],
                             statusLocs=[{'parent':statusFrame,'row':1,'column':1}],
                             label=u'CO\u2082'
                             )
    sensorMfcN2  = Erl2Input(sensorType='mfc.n2',
                             displayLocs=[{'parent':root,'row':1,'column':2}],
                             statusLocs=[{'parent':statusFrame,'row':2,'column':1}],
                             label=u'N\u2082'
                             )

    controlMfcAir = Erl2Mfc(controlType='mfc.air',
                            displayLocs=[{'parent':root,'row':2,'column':0}],
                            entryLoc={'parent':root,'row':3,'column':0},
                            )
    controlMfcCO2 = Erl2Mfc(controlType='mfc.co2',
                            displayLocs=[{'parent':root,'row':2,'column':1}],
                            entryLoc={'parent':root,'row':3,'column':1},
                            )
    controlMfcN2 =  Erl2Mfc(controlType='mfc.n2',
                            displayLocs=[{'parent':root,'row':2,'column':2}],
                            entryLoc={'parent':root,'row':3,'column':2},
                            )
    controlMfcAir.setActive()
    controlMfcCO2.setActive()
    controlMfcN2.setActive()
    root.mainloop()

if __name__ == "__main__": main()

