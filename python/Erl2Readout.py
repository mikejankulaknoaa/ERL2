from datetime import datetime as dt
from datetime import timezone as tz
from random import random as random
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2Plot import Erl2Plot
from Erl2State import Erl2State

SUBS=['temperature','pH','DO']
CTRLS={'temperature':['heater','chiller'],
       'pH':['mfc.air','mfc.co2'],
       'DO':['mfc.air','mfc.n2']}
LBLS={'temperature':['Heater','Chiller'],
      'pH':['Air',u'CO\u2082'],
      'DO':['Air',u'N\u2082']}
PLOTS={'temperature':['heater','chiller'],
      'pH':['mfc.air','mfc.co2'],
      'DO':['mfc.air','mfc.n2']}
PLOTSPECS={'heater': {'yLabel':'Heat',   'yLimit':1.,    'yColor':'red'},
           'chiller':{'yLabel':'Chill',  'yLimit':1.,    'yColor':'blue'},
           'mfc.air':{'yLabel':'Air',    'yLimit':5000., 'yColor':'deepskyblue'},
           'mfc.co2':{'yLabel':'$CO_2$', 'yLimit':20.,   'yColor':'grey'},
           'mfc.n2': {'yLabel':'$N_2$',  'yLimit':5000., 'yColor':'limegreen'}}

class Erl2Readout():

    def __init__(self,
                 labelText=None,
                 deviceState=None,
                 deviceLog=None,
                 displayLoc={},
                 erl2context={}):

        self.__labelText = labelText
        self.__deviceState = deviceState
        self.__deviceLog = deviceLog
        self.__displayLoc = displayLoc
        self.erl2context = erl2context

        # is the device state properly configured for readout?
        if self.__deviceState is None or type(self.__deviceState) is not Erl2State:
            raise TypeError(f"{self.__class__.__name__}: deviceState is not properly defined")

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']
        self.__lapseTime = self.erl2context['conf']['network']['lapseTime']

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load the images needed for readouts
        for i in ['button-grey-30.png',
                  'button-red-30.png',
                  'button-blue-30.png',
                  'network-off-25.png',
                  'network-on-25.png',
                  ]:
            self.erl2context['img'].addImage(i,i)

        # hardcode which image is which (heater, then chiller)
        self.__displayImages = [ ['button-grey-30.png','button-red-30.png'],
                                 ['button-grey-30.png','button-blue-30.png'] ]

        # hardcode which image is which (online status)
        self.__onlineImages = ['network-off-25.png','network-on-25.png']

        # remember what widgets are active for this readout
        self.__onlineWidget = None
        self.__labelWidget = None
        self.__displayWidgets = {}
        self.__allWidgets = []

        # remember which plots have been created in this Readout
        self.__allPlots = []

        # if using a virtualTemp sensor, it will be explicitly enabled in the state file
        self.__virtualTemp = (    self.__deviceState.isType('virtualtemp')
                              and self.__deviceState.get('virtualtemp','enabled',False))

        # create the main readout parent frame (no border, no padding)
        self.__parentFrame = ttk.Frame(self.__displayLoc['parent'], padding='0 0', relief='flat', borderwidth=0)

        # exact grid location might not be defined at readout creation time
        if (        'row' in self.__displayLoc and self.__displayLoc['row'] is not None
                and 'column' in self.__displayLoc and self.__displayLoc['column'] is not None):
            self.__parentFrame.grid(row=self.__displayLoc['row'], column=self.__displayLoc['column'], padx='0', pady='0', sticky='nesw')

        # column count in first row
        c1 = -1

        # readouts have two rows, each with their own frame
        f1 = ttk.Frame(self.__parentFrame, padding='0', relief='flat', borderwidth=0)
        f1.grid(row=0, column=0, padx='0', pady='0', sticky='nesw')
        f2 = ttk.Frame(self.__parentFrame, padding='0', relief='flat', borderwidth=0)
        f2.grid(row=1, column=0, padx='0', pady='0', sticky='nesw')

        # at startup, figure out how long it's been since a network update
        self.__online = 1
        self.checkOnline()
        lastActive = self.__deviceState.get('network','lastActive',None)
        currentTime = dt.now(tz=tz.utc)
        if lastActive is None or currentTime.timestamp() - lastActive.timestamp() > self.__lapseTime:
            self.__online = 0

        # add a widget to indicate online/offline depending on time since last update
        c1 += 1
        l = ttk.Label(f1, image=self.erl2context['img'][self.__onlineImages[self.__online]]
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=c1, sticky='ew')
        self.__onlineWidget = l
        self.__allWidgets.append(l)

        # device label in first row
        c1 += 1
        l = ttk.Label(f1, text=self.__labelText, font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=c1, sticky='ew')
        self.__labelWidget = l
        self.__allWidgets.append(l)

        # loop through list of possible subsystems
        self.__subSystemCount = 0
        for sub in SUBS:

            # is this subSystem present?
            if self.__deviceState.isType(sub):

                # create subSystem widgets dict
                if sub not in self.__displayWidgets:
                    self.__displayWidgets[sub] = {}

                # frame for sensor info
                sensorF = ttk.Frame(f2, padding='2', relief='solid', borderwidth=1)
                sensorF.grid(row=1, column=3*self.__subSystemCount, padx='2', pady='2', sticky='nesw')

                # frame for control info
                controlF = ttk.Frame(f2, padding='2', relief='solid', borderwidth=1)
                controlF.grid(row=1, column=3*self.__subSystemCount+1, padx='2', pady='2', sticky='nesw')

                # frame for plots
                plotF = ttk.Frame(f2, padding='2', relief='solid', borderwidth=1)
                plotF.grid(row=1, column=3*self.__subSystemCount+2, padx='2', pady='2', sticky='nesw')

                # label for sensor frame
                sensorLabel = None
                if sub == 'temperature':
                    sensorLabel = u'Temperature (\u00B0C)'
                    if self.__virtualTemp:
                        tempLabel = u'Virtual Temp (\u00B0C)'
                elif sub == 'pH':
                    sensorLabel = 'pH (Total Scale)'
                elif sub == 'DO':
                    sensorLabel = u'DO (\u00B5mol L\u207B\u00B9)'

                if sensorLabel is not None:
                    ttk.Label(sensorF, text=sensorLabel, font='Arial 12 bold'
                        #, relief='solid', borderwidth=1
                        ).grid(row=0, column=0, sticky='nw')

                # sensor value readout (e.g. as in Erl2Sensor)
                f = ttk.Frame(sensorF, padding='2 2', relief='flat', borderwidth=0)
                f.grid(row=1, column=0, padx='2', pady='0', sticky='nesw')
                l = ttk.Label(f, text='--', font='Arial 40 bold', foreground='#1C4587', justify='center'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, sticky='n')
                f.rowconfigure(0,weight=1)
                f.columnconfigure(0,weight=1)
                self.__displayWidgets[sub]['sensor'] = l
                self.__allWidgets.append(l)

                # sensor setpoint readout (e.g. as in Erl2SubSystem)
                f = ttk.Frame(sensorF, padding='0 0', relief='flat', borderwidth=0)
                f.grid(row=2, column=0, padx='2', pady='0', sticky='n')
                l = ttk.Label(f, text='--', font='Arial 20'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, sticky='nesw')
                f.rowconfigure(0,weight=1)
                f.columnconfigure(0,weight=1)
                self.__displayWidgets[sub]['setpoint'] = l
                self.__allWidgets.append(l)

                # sensor mode readout (e.g. as in Erl2SubSystem)
                f = ttk.Frame(sensorF, padding='0 0', relief='flat', borderwidth=0)
                f.grid(row=3, column=0, padx='2', pady='0', sticky='n')
                l = ttk.Label(f, text='--', font='Arial 10 bold italic'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=3, column=0, sticky='nesw')
                f.rowconfigure(0,weight=1)
                f.columnconfigure(0,weight=1)
                self.__displayWidgets[sub]['mode'] = l
                self.__allWidgets.append(l)

                # sensor lastValid readout

                # label for controls frame
                controlLabel = None
                if sub in ['pH', 'DO']:
                    controlLabel = u'Gas Flow (mL min\u207B\u00B9)'

                if controlLabel is not None:
                    ttk.Label(controlF, text=controlLabel, font='Arial 12 bold'
                        #, relief='solid', borderwidth=1
                        ).grid(row=0, column=0, sticky='nw')

                # each subsystem currently has two controls (hardcoded for now)
                controlList = CTRLS[sub]
                labelList = LBLS[sub]

                # build out readouts for each control in the subsystem
                for ind in range(0,len(controlList)):

                    # temperature looks a little different from the others
                    if sub == 'temperature':

                        # control setting readouts and labels (e.g. as in Erl2Toggle)
                        f = ttk.Frame(controlF, padding='2 2', relief='flat', borderwidth=0)
                        f.grid(row=ind+1, column=0, padx='2', pady='2', sticky='nesw')

                        # add a Label widget to show the current control value
                        l = ttk.Label(f, image=self.erl2context['img']['button-grey-30.png']
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=1, padx='2 2', sticky='e')
                        self.__displayWidgets[sub][controlList[ind] + '.setting'] = l
                        self.__allWidgets.append(l)

                        # this is the (text) Label shown beside the (image) display widget
                        ttk.Label(f, text=labelList[ind], font='Arial 16'
                            #, relief='solid', borderwidth=1
                            ).grid(row=0, column=0, padx='2 2', sticky='w')

                        f.rowconfigure(0,weight=1)
                        f.columnconfigure(1,weight=1)
                        f.columnconfigure(0,weight=0)

                    # mfcs have both settings and "sensor" readouts (e.g. as in Erl2Mfc, Erl2Sensor)
                    else:

                        # control "sensor" readouts and labels (e.g. as in Erl2Sensor)
                        f = ttk.Frame(controlF, padding='2 2', relief='flat', borderwidth=0)
                        f.grid(row=2*ind+1, column=0, padx='2', pady='0', sticky='nesw')

                        # add a Label widget to show the current control value
                        l = ttk.Label(f, text='--', font='Arial 19 bold', foreground='#1C4587')
                        l.grid(row=0, column=1, padx='2', sticky='e')
                        self.__displayWidgets[sub][controlList[ind] + '.value'] = l
                        self.__allWidgets.append(l)

                        # this is the Label shown beside the text display widget
                        ttk.Label(f, text=labelList[ind], font='Arial 16'
                            #, relief='solid', borderwidth=1
                            ).grid(row=0, column=0, padx='2 2', sticky='w')

                        f.rowconfigure(0,weight=1)
                        f.columnconfigure(0,weight=1,minsize=45)
                        f.columnconfigure(1,weight=1,minsize=76)

                        # control setting readouts and labels (e.g. as in Erl2Mfc)
                        f = ttk.Frame(controlF, padding='2 2', relief='flat', borderwidth=0)
                        f.grid(row=2*ind+2, column=0, padx='2', pady='0', sticky='nesw')

                        # add a Label widget to show the current MFC flow rate
                        l = ttk.Label(f, text='--', font='Arial 8', justify='right'
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=1, padx='2', pady='0', sticky='e')
                        self.__displayWidgets[sub][controlList[ind] + '.setting'] = l
                        self.__allWidgets.append(l)

                        # this is the Label shown beside the text display widget
                        ttk.Label(f, text='Setting', font='Arial 8'
                            #, relief='solid', borderwidth=1
                            ).grid(row=0, column=0, padx='2', pady='0', sticky='w')

                        f.rowconfigure(0,weight=1)
                        f.columnconfigure(0,weight=1,minsize=45)
                        f.columnconfigure(1,weight=1,minsize=76)

                    # note: ignoring lastValid info for control "sensors"

                # if provided with log data, draw a plot of sensor + control data
                if self.__deviceLog is not None and type(self.__deviceLog) is Erl2Log:

                    # build up the displaySpecs we need to send
                    dSpecs = []

                    # first, the specs for the sensor plot
                    dSpecs.append({'yName':sub, 'yParameter':f"s.{sub}.avg", 'yLabel':None, 'yLimit':None, 'yColor':'black'})

                    # then the associated controls
                    for ctrl in PLOTS[sub]:

                        # use a dict union (python 3.9 or higher)
                        dSpecs.append({'yName':ctrl, 'yParameter':f"c.{ctrl}.avg"} | PLOTSPECS[ctrl])

                    # now create the actual plot
                    thisPlot = Erl2Plot(plotLoc={'parent':plotF,'row':0,'column':0},
                                       #figsize=(2.500,1.000),
                                       figsize=(3.000,0.250),
                                       displayData=[self.__deviceLog],
                                       displaySpecs=dSpecs,
                                       #displayDecimals=None,
                                       )

                    # keep a list of plots we've created here
                    self.__allPlots.append(thisPlot)

                # increment subsystem count
                self.__subSystemCount += 1

        # try an initial "refresh" of values when initialization is done
        self.refreshDisplays()

        # last step is, start monitoring for inactivity
        self.checkInactivity()

    def refreshDisplays(self):

        # just in case, update the virtualtemp status every time this is called
        self.__virtualTemp = (    self.__deviceState.isType('virtualtemp')
                              and self.__deviceState.get('virtualtemp','enabled',False))

        # loop through list of possible subsystems
        self.__subSystemCount = 0
        for sub in SUBS:

            # is this subSystem present?
            if self.__deviceState.isType(sub):

                # 'temperature' might really mean 'virtualtemp'
                sensorName = sub
                if sensorName == 'temperature' and self.__virtualTemp:
                    sensorName = 'virtualtemp'

                # get current parameter values from device's state file
                online = self.__deviceState.get(sensorName,'online',False)
                value = self.__deviceState.get(sensorName,'value',None)
                displayDecimals = self.__deviceState.get(sensorName,'displayDecimals',0)

                # these pertain to the subsystem not the sensor
                ctrl = self.__deviceState.get(sub,'ctrl',None)
                mode = self.__deviceState.get(sub,'mode',None)
                activeSetpoint = self.__deviceState.get(sub,'activeSetpoint',None)

                #print (f"{self.__class__.__name__}: Debug: refreshDisplays() online [{online}][{type(online)}],"
                #       f"value [{value}][{type(value)}], displayDecimals [{displayDecimals}][{type(displayDecimals)}]")

                # figure out what values to use in updates
                valueText = setpointText = modeText = '--'
                if online:
                    # format the value for display, and change to string
                    if value is not None:
                        valueText = f"{round(float(value),displayDecimals):.{displayDecimals}f}"

                # format the setpoint for display, and change to string
                if activeSetpoint is not None:
                    setpointText = f"{round(float(activeSetpoint),displayDecimals):.{displayDecimals}f}"

                # figure out what the text description of the mode should be
                if ctrl is not None and mode is not None:
                    modeText = ['Local','Controller'][ctrl] + '/' + ['Manual','Static','Dynamic'][mode]

                # update the displays
                self.__displayWidgets[sub]['sensor'].config(text=valueText)
                self.__displayWidgets[sub]['setpoint'].config(text=setpointText)
                self.__displayWidgets[sub]['mode'].config(text=modeText)

                # each subsystem currently has two controls (hardcoded for now)
                controlList = CTRLS[sub]

                # now loop through controls for this subsystem
                for ind in range(0,len(controlList)):

                    # temperature looks a little different from the others
                    if sub == 'temperature':

                        # get current parameter settings from device's state file
                        setting = int(self.__deviceState.get(controlList[ind],'setting',0))

                        # update the display with the appropriate image
                        #print (f"{self.__class__.__name__}: Debug: refreshDisplays() widget [{controlList[ind] + '.setting'}], "
                        #       f"image [{self.erl2context['img'][self.__displayImages[ind][setting]]}], setting [{setting}]")
                        self.__displayWidgets[sub][controlList[ind] + '.setting'].config(
                            image=self.erl2context['img'][self.__displayImages[ind][setting]])

                    # pH and DO have both control /values/ (read back from MFCs as if they are "sensors")
                    # and control /settings/ (manual or auto static/dynamic settings "requested" of the MFCs)
                    else:

                        # get current parameter values from device's state file
                        online = self.__deviceState.get(controlList[ind],'online',False)
                        value = self.__deviceState.get(controlList[ind],'value',None)
                        displayDecimals = self.__deviceState.get(controlList[ind],'displayDecimals',0)
                        setting = self.__deviceState.get(controlList[ind],'setting',None)

                        # figure out what values to use in updates
                        valueText = settingText = '--'
                        if online:
                            # format the value for display, and change to string
                            if value is not None:
                                valueText = f"{round(float(value),displayDecimals):.{displayDecimals}f}"

                        # format the setting for display, and change to string
                        if setting is not None:
                            settingText = f"{round(float(setting),displayDecimals):.{displayDecimals}f}"

                        # update the displays
                        self.__displayWidgets[sub][controlList[ind] + '.value'].config(text=valueText)
                        self.__displayWidgets[sub][controlList[ind] + '.setting'].config(text=settingText)

        # also update the plots in this Readout
        for p in self.__allPlots:
            p.updatePlot()

    def checkOnline(self):

        lastActive = self.__deviceState.get('network','lastActive',None)
        currentTime = dt.now(tz=tz.utc)
        if lastActive is None or currentTime.timestamp() - lastActive.timestamp() > self.__lapseTime:
            self.__online = 0
        else:
            self.__online = 1

    def checkInactivity(self):

        # first, refresh online status
        self.checkOnline()

        # next, apply correct image to online widget
        if self.__onlineWidget is not None:
            self.__onlineWidget.configure(image=self.erl2context['img'][self.__onlineImages[self.__online]])

            # call this method again after 5 seconds
            self.__onlineWidget.after(5000, self.checkInactivity)

def main():

    #readout = Erl2Readout()
    print ("Erl2Readout module (cannot be used apart from Erl2Controller)")

if __name__ == "__main__": main()

