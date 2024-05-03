# ignore any failure to load hardware libraries on windows
_hwLoaded = True
try:
    from megaind import get4_20In, get0_10In
except:
    _hwLoaded = False

import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Sensor import Erl2Sensor

# any device connected to one of the Sequent Microsystems' four 4-20 mA input channels,
# or (optionally) one of its 0-10V input channels

class Erl2Input(Erl2Sensor):

    def __init__(self,
                 sensorType='generic',
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 label=None,
                 erl2context={}):

        # call the Erl2Sensor class's constructor
        super().__init__(sensorType=sensorType,
                         displayLocs=displayLocs,
                         statusLocs=statusLocs,
                         correctionLoc=correctionLoc,
                         label=label,
                         erl2context=erl2context)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # trigger an error if this isn't windows and the hardware lib wasn't found
        assert(_hwLoaded or self.erl2context['conf']['system']['platform'] in ['darwin','win32'])

        # private attributes specific to Erl2Input
        self.__stackLevel = self.erl2context['conf'][self.sensorType]['stackLevel']
        self.__inputChannel = self.erl2context['conf'][self.sensorType]['inputChannel']
        self.__channelType = self.erl2context['conf'][self.sensorType]['channelType']
        self.__parameterName = self.erl2context['conf'][self.sensorType]['parameterName']
        self.__hardwareMin = self.erl2context['conf'][self.sensorType]['hardwareRange'][0]
        self.__hardwareMax = self.erl2context['conf'][self.sensorType]['hardwareRange'][1]

        # some measurement constants depend on whether this is 0-10 V or 4-20 mA
        self.__minVal = self.__maxVal = self.__bufferVal = None
        if self.__channelType == 'volts':
            self.__minVal = 0.
            self.__maxVal = 10.
            self.__bufferVal = 0.25
        elif self.__channelType == 'milliAmps':
            self.__minVal = 4.
            self.__maxVal = 20.
            self.__bufferVal = 0.4

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Input or a child class)
        if self.__class__.__name__ == 'Erl2Input':
            self.readSensor()

    def measure(self):

        # initialize the measurement result
        self.value = {}

        # ignore missing hardware libraries on windows
        if _hwLoaded:

            if self.__channelType == 'volts':
                # read volts from the input channel
                measuredVal = get0_10In(self.__stackLevel, self.__inputChannel)

            elif self.__channelType == 'milliAmps':
                # read milliAmps from the input channel
                measuredVal = get4_20In(self.__stackLevel, self.__inputChannel)

            else:
                measuredVal = float('nan')

        else:
            measuredVal = float('nan')

        # check result: by definition this should be within 0-10V or 4-20mA
        # (however: allow values slightly outside this range because when
        # legitimately reporting sensor's min or max values there is often
        # some noise around the readings at both edges of the range)
        if measuredVal >= (self.__minVal-self.__bufferVal) and measuredVal <= (self.__maxVal+self.__bufferVal):

            # add raw measurement to the results
            self.value[self.__channelType] = measuredVal

            # convert from volts or milliAmps to a value in the defined hardwareRange
            self.value[self.__parameterName] = ( (measuredVal - self.__minVal)
                                               / (self.__maxVal-self.__minVal)
                                               * (self.__hardwareMax - self.__hardwareMin)
                                               + self.__hardwareMin
                                               )

        # check if we're still/currently offline
        self.online = not (self.value == {})

        # add Timestamps to measurement record
        t, m = self.getTimestamp()

        # produce the final measurement dict with timestamps and values
        self.value = {**m, **self.value}

        # remember timestamp of last valid measurement
        if self.online:
            self.lastValid = t

        #print (f"{self.__class__.__name__}: Debug: measure() returning [{str(t)}][{str(self.value)}][{str(self.online)}]")

        # apply the corrective offset
        self.applyOffset(self.value, updateRaw=True)

        # return timestamp, measurement and status
        return t, self.value, self.online

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Input',font='Arial 30 bold').grid(row=0,column=0,columnspan=4)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0,columnspan=4)
    ttk.Label(statusFrame,text='Temperature last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')
    ttk.Label(statusFrame,text='Air MFC last read:',font='Arial 14 bold',justify='right').grid(row=1,column=0,sticky='nes')
    ttk.Label(statusFrame,text='CO2 MFC last read:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nes')
    ttk.Label(statusFrame,text='N2 MFC last read:',font='Arial 14 bold',justify='right').grid(row=3,column=0,sticky='nes')

    temperature = Erl2Input(sensorType='temperature',
                            displayLocs=[{'parent':root,'row':1,'column':0}],
                            statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                            correctionLoc={'parent':root,'row':2,'column':0})
    mfcAir =      Erl2Input(sensorType='mfc.air',
                            displayLocs=[{'parent':root,'row':1,'column':1}],
                            statusLocs=[{'parent':statusFrame,'row':1,'column':1}])
    mfcCO2 =      Erl2Input(sensorType='mfc.co2',
                            displayLocs=[{'parent':root,'row':1,'column':2}],
                            statusLocs=[{'parent':statusFrame,'row':2,'column':1}])
    mfcN2  =      Erl2Input(sensorType='mfc.n2',
                            displayLocs=[{'parent':root,'row':1,'column':3}],
                            statusLocs=[{'parent':statusFrame,'row':3,'column':1}])

    root.mainloop()

if __name__ == "__main__": main()

