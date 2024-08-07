from datetime import datetime as dt
from datetime import timezone as tz
from random import random as random
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2Plot import Erl2Plot
from Erl2Popup import Erl2Popup
from Erl2State import Erl2State
from Erl2Useful import SUBSYSTEMS

SUBSYSTEM_CTRLS = {'temperature':['heater','chiller'],
                   'pH':['mfc.air','mfc.co2'],
                   'DO':['mfc.air','mfc.n2']}
SUBSYSTEM_LBLS = {'temperature':['Heater','Chiller'],
                  'pH':['Air',u'CO\u2082'],
                  'DO':['Air',u'N\u2082']}
SUBSYSTEM_PLOTS = {'temperature':['heater','chiller'],
                   'pH':['mfc.air','mfc.co2'],
                   'DO':['mfc.air','mfc.n2']}

class Erl2Readout():

    def __init__(self,
                 labelText=None,
                 mac=None,
                 displayLoc={},
                 erl2context={}):

        self.__labelText = labelText
        self.__mac = mac
        self.__displayLoc = displayLoc
        self.erl2context = erl2context

        #print (f"{self.__class__.__name__}: Debug: __init__: mac [{self.__mac}]")

        # use the MAC address to get the right Erl2State and Erl2Log instances
        self.__deviceState = self.__deviceLog = None
        if 'network' in self.erl2context:
            self.__deviceState = self.erl2context['network'].childrenStates[self.__mac]
            self.__deviceLog = self.erl2context['network'].childrenLogs[self.__mac]

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
                  'edit-25.png',
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
        self.__online = True
        self.checkOnline()
        lastActive = self.__deviceState.get('network','lastActive',None)
        currentTime = dt.now(tz=tz.utc)
        if lastActive is None or currentTime.timestamp() - lastActive.timestamp() > self.__lapseTime:
            self.__online = False

        # add a widget to indicate network online/offline status depending on time since last update
        c1 += 1
        l = ttk.Label(f1, image=self.erl2context['img'][self.__onlineImages[self.__online]]
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=c1, sticky='ew')
        self.__onlineWidget = l

        # device label in first row
        c1 += 1
        l = ttk.Label(f1, text=self.__labelText, font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=c1, sticky='ew')
        self.__labelWidget = l

        # add a button to edit this particular tank's settings
        c1 += 1
        l = ttk.Label(f1, image=self.erl2context['img']['edit-25.png']
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=c1, sticky='e')
        self.__editWidget = l
        self.__editWidget.bind('<Button-1>',
            lambda event, tp='Edit Tank Settings', mac=self.__mac, cx=self.erl2context: Erl2Popup.openPopup(popupType=tp, mac=mac, erl2context=cx))

        f1.rowconfigure(0,weight=1)
        f1.columnconfigure(0,weight=0)
        f1.columnconfigure(1,weight=0)
        f1.columnconfigure(2,weight=1)

        # loop through list of possible subsystems
        self.__subSystemCount = 0
        for sub in SUBSYSTEMS:

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
                if  self.erl2context['state'].get('system','plots',1):
                    plotF = ttk.Frame(f2, padding='2', relief='solid', borderwidth=1)
                    plotF.grid(row=1, column=3*self.__subSystemCount+2, padx='2', pady='2', sticky='nesw')

                # label for sensor frame
                sensorLabel = None
                if sub == 'temperature':
                    sensorLabel = u'Temperature (\u00B0C)'
                    if self.__virtualTemp:
                        sensorLabel = u'Virtual Temp (\u00B0C)'
                elif sub == 'pH':
                    sensorLabel = 'pH (Total Scale)'
                elif sub == 'DO':
                    sensorLabel = u'DO (\u00B5mol  L\u207B\u00B9)    '
                    if self.erl2context['conf']['DO']['displayParameter'] == 'mgL':
                        sensorLabel = u'DO (mg L\u207B\u00B9)'

                if sensorLabel is not None:
                    l = ttk.Label(sensorF, text=sensorLabel, font='Arial 12 bold'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=0, column=0, sticky='nw')
                    self.__displayWidgets[sub]['sens.label'] = l

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

                # sensor lastValid readout

                # label for controls frame
                controlLabel = None
                if sub in ['pH', 'DO']:
                    controlLabel = u'Gas Flow (mL min\u207B\u00B9)'

                if controlLabel is not None:
                    l = ttk.Label(controlF, text=controlLabel, font='Arial 12 bold'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=0, column=0, sticky='nw')
                    self.__displayWidgets[sub]['ctrl.label'] = l

                # each subsystem currently has two controls (hardcoded for now)
                controlList = SUBSYSTEM_CTRLS[sub]
                labelList = SUBSYSTEM_LBLS[sub]

                # build out readouts for each control in the subsystem
                for ind in range(0,len(controlList)):

                    # temperature looks a little different from the others
                    if sub == 'temperature':

                        # control value readouts and labels (e.g. as in Erl2Toggle)
                        f = ttk.Frame(controlF, padding='2 2', relief='flat', borderwidth=0)
                        f.grid(row=ind+1, column=0, padx='2', pady='2', sticky='nesw')

                        # add a Label widget to show the current control setting
                        l = ttk.Label(f, image=self.erl2context['img']['button-grey-30.png']
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=1, padx='2 2', sticky='e')
                        self.__displayWidgets[sub][controlList[ind] + '.setting'] = l

                        # this is the (text) Label shown beside the (image) display widget
                        l = ttk.Label(f, text=labelList[ind], font='Arial 16'
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=0, padx='2 2', sticky='w')
                        self.__displayWidgets[sub][controlList[ind] + '.set.label'] = l

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

                        # this is the Label shown beside the text display widget
                        l = ttk.Label(f, text=labelList[ind], font='Arial 16'
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=0, padx='2 2', sticky='w')
                        self.__displayWidgets[sub][controlList[ind] + '.val.label'] = l

                        f.rowconfigure(0,weight=1)
                        f.columnconfigure(0,weight=1,minsize=45)
                        f.columnconfigure(1,weight=1,minsize=76)

                        # control setting readouts and labels (e.g. as in Erl2Mfc)
                        f = ttk.Frame(controlF, padding='2 2', relief='flat', borderwidth=0)
                        f.grid(row=2*ind+2, column=0, padx='2', pady='0', sticky='nesw')

                        # add a Label widget to show the current (requested setting) MFC flow rate
                        l = ttk.Label(f, text='--', font='Arial 8', justify='right'
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=1, padx='2', pady='0', sticky='e')
                        self.__displayWidgets[sub][controlList[ind] + '.setting'] = l

                        # this is the Label shown beside the text display widget
                        l =ttk.Label(f, text='Setting', font='Arial 8'
                            #, relief='solid', borderwidth=1
                            )
                        l.grid(row=0, column=0, padx='2', pady='0', sticky='w')
                        self.__displayWidgets[sub][controlList[ind] + '.set.label'] = l

                        f.rowconfigure(0,weight=1)
                        f.columnconfigure(0,weight=1,minsize=45)
                        f.columnconfigure(1,weight=1,minsize=76)

                    # note: ignoring lastValid info for control "sensors"

                # if provided with log data, draw a plot of sensor + control data (unless plots are disabled system-wide)
                if (    self.__deviceLog is not None
                    and type(self.__deviceLog) is Erl2Log
                    and self.erl2context['state'].get('system','plots',1)):

                    # build up the displaySpecs we need to send
                    dSpecs = []

                    # first, the specs for the sensor plot
                    dSpecs.append({'yName':sub, 'yParameter':f"s.{sub}"})

                    # then the associated controls
                    for ctrl in SUBSYSTEM_PLOTS[sub]:
                        dSpecs.append({'yName':ctrl, 'yParameter':f"c.{ctrl}.avg"})

                    # now create the actual plot
                    thisPlot = Erl2Plot(plotLoc={'parent':plotF,'row':0,'column':0},
                                        #figsize=(2.500,1.000),
                                        figsize=(3.000,0.250),
                                        displayData=[self.__deviceLog],
                                        displaySpecs=dSpecs,
                                        #displayDecimals=None,
                                        erl2context=self.erl2context,
                                        )

                    # keep a list of plots we've created here
                    self.__allPlots.append(thisPlot)

                # increment subsystem count
                self.__subSystemCount += 1

        # try an initial "refresh" of values when initialization is done
        self.refreshDisplays()

        # last step is, start monitoring for inactivity
        self.__checkInactivityTime = None
        self.checkInactivity()

    def refreshDisplays(self):

        # just in case, update the virtualtemp status every time this is called
        self.__virtualTemp = (    self.__deviceState.isType('virtualtemp')
                              and self.__deviceState.get('virtualtemp','enabled',False))

        # loop through list of possible subsystems
        self.__subSystemCount = 0
        for sub in SUBSYSTEMS:

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
                actualCtrl = self.__deviceState.get(sub,'ctrl.actual',None)
                actualMode = self.__deviceState.get(sub,'mode.actual',None)
                activeSetpoint = self.__deviceState.get(sub,'activeSetpoint',None)

                # if the tank provides actual control/mode info, use it
                if actualCtrl is not None: ctrl = actualCtrl
                if actualMode is not None: mode = actualMode

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
                    modeText = ['Offline','Local','Controller'][ctrl] + '/' + ['Manual','Static','Dynamic'][mode]

                # update the displays
                self.__displayWidgets[sub]['sensor'].config(text=valueText)
                self.__displayWidgets[sub]['setpoint'].config(text=setpointText)
                self.__displayWidgets[sub]['mode'].config(text=modeText)

                # each subsystem currently has two controls (hardcoded for now)
                controlList = SUBSYSTEM_CTRLS[sub]

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

        oldStatus = self.__online

        lastActive = self.__deviceState.get('network','lastActive',None)
        currentTime = dt.now(tz=tz.utc)
        if lastActive is None or currentTime.timestamp() - lastActive.timestamp() > self.__lapseTime:
            self.__online = False
        else:
            self.__online = True

        # return true if new status was set
        return oldStatus != self.__online

    def checkInactivity(self):

        # what is the current time?
        currentTime = dt.now(tz=tz.utc)

        # first, refresh this Readout's online status, and widget color
        changed = self.checkOnline()
        wSensorColor = '#1C4587' # blue
        wOtherColor = '' # I think this will set it to the default text color
        wState = 'normal'
        if not self.__online:
            wSensorColor = wOtherColor = 'grey'
            wState = 'disabled'

        # always apply correct image to any online widget
        if self.__onlineWidget is not None:
            self.__onlineWidget.configure(image=self.erl2context['img'][self.__onlineImages[self.__online]])

        # status recently changed, or it's been a minute since refreshing?
        if (changed or self.__checkInactivityTime is None or currentTime.timestamp() - self.__checkInactivityTime.timestamp() > 60):

            self.__checkInactivityTime = currentTime

            # loop through possible subsystems
            for sub in SUBSYSTEMS:

                # is this subSystem present?
                if sub in self.__displayWidgets:

                    # loop through all associated widgets
                    for w in self.__displayWidgets[sub]:

                        # sensor, and control/sensors, are blue or grey
                        if w == 'sensor' or '.value' in w:
                            self.__displayWidgets[sub][w].config(foreground=wSensorColor)

                        # control setting, if an image label, gets disabled/normal state
                        elif '.setting' in w and len(self.__displayWidgets[sub][w].cget('text')) == 0:
                            #print (f"{self.__class__.__name__}: Debug: checkInactivity({self.__labelText}) [{sub}][{w}] text is [{self.__displayWidgets[sub][w].cget('text')}]")
                            self.__displayWidgets[sub][w].config(state=wState)

                        # all others -- textual control settings, control values, setpoints, modes -- are dafault (black?) or grey
                        else:
                            self.__displayWidgets[sub][w].config(foreground=wOtherColor)

            # also update the plots in this Readout
            for p in self.__allPlots:
                p.updatePlot(online=self.__online)

        # call this method again after 5 seconds
        self.__onlineWidget.after(5000, self.checkInactivity)

def main():

    #readout = Erl2Readout()
    print ("Erl2Readout module (cannot be used apart from Erl2Controller)")

if __name__ == "__main__": main()

