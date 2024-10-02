from datetime import datetime as dt
from datetime import timezone as tz
from math import isnan
from re import sub
from simple_pid import PID
from sys import version_info
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2Plot import Erl2Plot
from Erl2MegaindOutput import Erl2MegaindOutput
from Erl2State import Erl2State
from Erl2Useful import OFFLINE,LOCAL,CONTROLLER,MANUAL,AUTO_STATIC,AUTO_DYNAMIC
from Erl2VirtualTemp import Erl2VirtualTemp

class Erl2SubSystem():

    def __init__(self,
                 subSystemType='generic',
                 logic='generic',

                 # these controls are unique and aren't cloned to more than one frame
                 ctrlRadioLoc={},
                 modeRadioLoc={},
                 staticSetpointLoc={},
                 hysteresisLoc=None,
                 dynamicSetpointsLoc={},

                 # these displays may be cloned to multiple tabs/frames
                 setpointDisplayLocs=[],
                 modeDisplayLocs=[],
                 plotDisplayLoc={},
                 statsDisplayLoc={},

                 radioImages=['radio-off-30.png','radio-on-30.png'],
                 sensors={},
                 toggles={},
                 MFCs={},
                 thisTabControls=[],
                 erl2context={}):

        self.subSystemType = subSystemType
        self.__logic = logic
        assert(self.__logic in ('generic','hysteresis','PID'))

        self.__ctrlRadioLoc = ctrlRadioLoc
        self.__modeRadioLoc = modeRadioLoc
        self.__staticSetpointLoc = staticSetpointLoc
        self.__hysteresisLoc = hysteresisLoc
        self.__dynamicSetpointsLoc = dynamicSetpointsLoc

        self.__plotDisplayLoc = plotDisplayLoc
        self.__statsDisplayLoc = statsDisplayLoc
        self.__plot = None
        self.__plotTracker = None
        self.__setpointDisplayLocs = setpointDisplayLocs
        self.__modeDisplayLocs = modeDisplayLocs

        self.radioImages = radioImages
        self.__sensors = sensors
        self.__toggles = toggles
        self.__MFCs = MFCs
        self.__thisTabControls = thisTabControls
        self.__controls = {**toggles, **MFCs}
        self.__PIDs = {}
        self.__pidParams = {}
        self.__pidLastUpdated = {}
        self.erl2context = erl2context

        # this module requires Python 3.7 or higher
        # (the release when dictionaries are guaranteed to be ordered)
        try:
            assert version_info > (3,7)
        except:
            print (f"{self.__class__.__name__}: Error: Python 3.7 or higher is required for this system")
            raise

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load the associated images; just use the image name as the key
        for i in self.radioImages:
            self.erl2context['img'].addImage(i,i)

        # keep a list of Entry widgets
        self.allEntries = []

        # start a data/log file for the subsystem
        self.log = Erl2Log(logType='subsystem', logName=self.subSystemType, erl2context=self.erl2context)

        # borrow the display settings from the sensor config
        self.__displayParameter = self.erl2context['conf'][self.subSystemType]['displayParameter']
        self.__displayDecimals = self.erl2context['conf'][self.subSystemType]['displayDecimals']
        self.__validRange = self.erl2context['conf'][self.subSystemType]['validRange']

        # other useful parameters from Erl2Config
        self.__modeDefault = self.erl2context['conf'][self.subSystemType]['modeDefault']
        self.__setpointDefault = self.erl2context['conf'][self.subSystemType]['setpointDefault']
        self.__dynamicDefault = self.erl2context['conf'][self.subSystemType]['dynamicDefault']

        # look up PID tuning parameters for the MFCs
        if self.__logic == 'PID':
            for mfc in self.__MFCs:
                self.__pidParams[mfc] = {}
                for param in 'Kp', 'Ki', 'Kd':
                    self.__pidParams[mfc][param] = self.erl2context['conf'][self.subSystemType][f"{mfc}.{param}"]
                    #print (f"{__class__.__name__}: Debug: PID param [{mfc}.{param}] [{self.__pidParams[mfc][param]}]")

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # also keep a float-valued record of the current values of these parameters
        self.staticSetpointFloat = self.erl2context['state'].get(self.subSystemType,'staticSetpoint',self.__setpointDefault)
        self.dynamicSetpointsFloat = self.erl2context['state'].get(self.subSystemType,'dynamicSetpoints',self.__dynamicDefault)

        # set up hysteresis logic, if applicable
        if self.__logic == 'hysteresis':

            self.__hysteresisDefault = self.erl2context['conf'][self.subSystemType]['hysteresisDefault']
            self.hysteresisFloat = self.erl2context['state'].get(self.subSystemType,'hysteresis',self.__hysteresisDefault)

            # try to reload metadata from the state file
            self.__hysteresisMetadata = self.erl2context['state'].get(self.subSystemType,'hysteresisMetadata',{})

            # discard metadata if incomplete or not recent enough
            if ('currentTime' not in self.__hysteresisMetadata
                or (  dt.now(tz=tz.utc).timestamp()
                    - self.__hysteresisMetadata['currentTime'].timestamp()
                    > self.erl2context['conf'][self.subSystemType]['loggingFrequency'])):

                self.__hysteresisMetadata = {}

        # remember what radio widgets and entry fields are active for this control
        self.__ctrlRadioWidgets = []
        self.__modeRadioWidgets = []
        self.staticSetpointEntry = None
        self.dynamicSetpointsEntry = []
        if self.__logic == 'hysteresis':
            self.hysteresisEntry = None

        # also keep track of display-only widgets
        self.__setpointDisplayWidgets = []
        self.__modeDisplayWidgets = []

        # remember if this subsystem's associated controls are enabled or not
        self.__controlsEnabled = None

        # the state of this subsystem is described by its mode and active setpoint
        self.__ctrlVar = tk.IntVar()
        self.__modeVar = tk.IntVar()
        self.__lastCtrlVar = None
        self.__lastModeVar = None
        self.__activeSetpoint = self.__setpointDefault

        # also we track the timing of the subsystem to a certain extent
        self.__hour = None
        self.__modeChanged = False
        self.__modeLastChanged = None
        self.__setpointLastChanged = None

        # a list of choices for the control radio buttons
        self.__ctrlDict = {OFFLINE:'Offline',
                           LOCAL:'Local',
                           CONTROLLER:'Controller'}

        # during initialization, the default is local control
        # (but see if there's a different setting in the system saved state)
        self.__ctrlVar.set(self.erl2context['state'].get(self.subSystemType,'ctrl',LOCAL))

        # make sure we're not exceeding array bounds
        if self.__ctrlVar.get() > len(self.__ctrlDict):
            self.__ctrlVar.set(len(self.__ctrlDict))

        # add radio buttons to toggle this subsystem's control mode
        if 'parent' in self.__ctrlRadioLoc:
            for value , text in self.__ctrlDict.items():

                # don't explicitly draw an Offline radio button (but adjust array indices by -1 later!)
                if value != OFFLINE:
                    r = tk.Radiobutton(self.__ctrlRadioLoc['parent'],
                                       indicatoron=0,
                                       image=self.erl2context['img'][self.radioImages[0]],
                                       selectimage=self.erl2context['img'][self.radioImages[1]],
                                       compound='left',
                                       font='Arial 16',
                                       bd=0,
                                       highlightthickness=0,
                                       background='#DBDBDB',
                                       activebackground='#DBDBDB',
                                       highlightcolor='#DBDBDB',
                                       highlightbackground='#DBDBDB',
                                       #bg='#DBDBDB',
                                       selectcolor='#DBDBDB',
                                       variable=self.__ctrlVar,
                                       value=value,
                                       text=' '+text,
                                       command=self.applyMode
                                       )
                    r.grid(row=ctrlRadioLoc['row']+value,column=0,ipadx=2,ipady=2,sticky='w')

                    self.__ctrlRadioWidgets.append(r)

        # a list of choices for the mode radio buttons
        self.__modeDict = {MANUAL:'Manual',
                           AUTO_STATIC:'Auto Static',
                           AUTO_DYNAMIC:'Auto Dynamic'}

        # during initialization, the default is determined by the erl2.conf file settings / defaults
        # (but see if there's a different setting in the system saved state)
        self.__modeVar.set(self.erl2context['state'].get(self.subSystemType,'mode',self.__modeDefault))

        # make sure we're not exceeding array bounds
        if self.__modeVar.get() > len(self.__modeDict):
            self.__modeVar.set(len(self.__modeDict))

        # add radio buttons to select this subsystem's mode setting
        if 'parent' in self.__modeRadioLoc:
            for value , text in self.__modeDict.items():
                r = tk.Radiobutton(self.__modeRadioLoc['parent'],
                                   indicatoron=0,
                                   image=self.erl2context['img'][self.radioImages[0]],
                                   selectimage=self.erl2context['img'][self.radioImages[1]],
                                   compound='left',
                                   font='Arial 16',
                                   bd=0,
                                   highlightthickness=0,
                                   background='#DBDBDB',
                                   activebackground='#DBDBDB',
                                   highlightcolor='#DBDBDB',
                                   highlightbackground='#DBDBDB',
                                   #bg='#DBDBDB',
                                   selectcolor='#DBDBDB',
                                   variable=self.__modeVar,
                                   value=value,
                                   text=' '+text,
                                   command=self.applyMode
                                   )
                r.grid(row=modeRadioLoc['row']+value,column=0,ipadx=2,ipady=2,sticky='w')

                self.__modeRadioWidgets.append(r)

        # create the static setpoint entry widget's base frame as a child of its parent
        if 'parent' in self.__staticSetpointLoc:
            f = ttk.Frame(self.__staticSetpointLoc['parent'], padding='2 2', relief='flat', borderwidth=0)
            f.grid(row=self.__staticSetpointLoc['row'], column=self.__staticSetpointLoc['column'], padx='2', pady='0', sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)
            f.columnconfigure(2,weight=0)

            # create the entry field for the static setpoint
            self.staticSetpointEntry = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                                                 labelLoc={'parent':f,'row':0,'column':0},
                                                 label='Static\nSetpoint',
                                                 width=5,
                                                 displayDecimals=self.__displayDecimals,
                                                 validRange=self.__validRange,
                                                 initValue=self.staticSetpointFloat,
                                                 onChange=self.changeStaticSetpoint,
                                                 erl2context=self.erl2context)

            # expose a list of all entry fields so it can be seen by other modules
            self.allEntries.append(self.staticSetpointEntry)

        # hysteresis is only used in certain subsystems
        if self.__logic == 'hysteresis' and self.__hysteresisLoc is not None and 'parent' in self.__hysteresisLoc:

            # create the hysteresis entry widget's base frame as a child of its parent
            f = ttk.Frame(self.__hysteresisLoc['parent'], padding='2 2', relief='flat', borderwidth=0)
            f.grid(row=self.__hysteresisLoc['row'], column=self.__hysteresisLoc['column'], padx='2', pady='0', sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)
            f.columnconfigure(2,weight=0)

            # create the entry field for the hysteresis parameter
            self.hysteresisEntry = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                                             labelLoc={'parent':f,'row':0,'column':0},
                                             label='Hysteresis',
                                             width=5,
                                             displayDecimals=(self.__displayDecimals+2),
                                             validRange=[0., None],
                                             initValue=self.hysteresisFloat,
                                             onChange=self.changeHysteresis,
                                             erl2context=self.erl2context)

            # expose a list of all entry fields so it can be seen by other modules
            self.allEntries.append(self.hysteresisEntry)

        # add dynamic setpoint entry fields

        # create the dynamic setpoint grid's base frame as a child of its parent
        if 'parent' in self.__dynamicSetpointsLoc:
            f = ttk.Frame(self.__dynamicSetpointsLoc['parent'], padding='2 2', relief='flat', borderwidth=0)
            f.grid(row=self.__dynamicSetpointsLoc['row'], column=self.__dynamicSetpointsLoc['column'], padx='2', pady='2', sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)
            f.columnconfigure(2,weight=0)

            hourNum = 0
            for hourVal in self.dynamicSetpointsFloat:

                # lay them out in two rows, 12 boxes each
                if hourNum < 12:
                    hourRow = 0
                    hourCol = hourNum
                    valRow = 1
                    valCol = hourNum
                    hourPady = '0 0'
                else:
                    hourRow = 2
                    hourCol = hourNum-12
                    valRow = 3
                    valCol = hourNum-12
                    hourPady = '4 0'

                # hour label for dynamic setpoints
                ttk.Label(f, text=str(hourNum), font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    ).grid(row=hourRow, column=hourCol, pady=hourPady, sticky='s')

                # create the entry field for each dynamic setpoint
                e = Erl2Entry(entryLoc={'parent':f,'row':valRow,'column':valCol},
                              #labelLoc={'parent':f,'row':0,'column':0},
                              #label='Static\nSetpoint',
                              width=5,
                              font='Arial 16',
                              displayDecimals=self.__displayDecimals,
                              validRange=self.__validRange,
                              initValue=hourVal,
                              onChange=self.changeDynamicSetpoint,
                              onChangeArg=hourNum,
                              erl2context=self.erl2context)

                self.dynamicSetpointsEntry.append(e)

                hourNum += 1

            # expose a list of all entry fields so it can be seen by other modules (first field only)
            self.allEntries.append(self.dynamicSetpointsEntry[0])

        # loop through the list of needed setpoint display widgets for this sensor
        for loc in self.__setpointDisplayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='flat', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current setpoint value
            l = ttk.Label(f, text=self.__activeSetpoint, font='Arial 20'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=0, sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)

            # keep a list of setpoint display widgets for this sensor
            self.__setpointDisplayWidgets.append(l)

        # loop through the list of needed mode display widgets for this sensor
        for loc in self.__modeDisplayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='flat', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current mode setting
            #txt = self.__modeDict[self.__modeVar.get()] + ' mode'
            txt = self.__ctrlDict[self.__ctrlVar.get()] + '/' + sub('^Auto ','',self.__modeDict[self.__modeVar.get()])
            l = ttk.Label(f, text=txt, font='Arial 10 bold italic'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=0, sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)

            # keep a list of mode display widgets for this sensor
            self.__modeDisplayWidgets.append(l)

        # call applyMode here to initialize button (in)activeness
        self.applyMode()

        # inform the controls about what subsystem they are part of
        for ctl in self.__controls.values():
            ctl.subSystem = self

        # set the focus to the first mode radio button
        self.__modeRadioWidgets[0].focus()

        # build a list of logs for plotting
        displayData = []
        displaySpecs = []
        for sens in self.__sensors:
            displayData.append(self.__sensors[sens].log)
            displaySpecs.append({'yName':sens,'yParameter':self.__displayParameter})
        for ctrl in self.__controls:
            displayData.append(self.__controls[ctrl].log)
            displaySpecs.append({'yName':ctrl,'yParameter':'Average Setting'})

        # draw a plot of the history of the subsystem (unless plots are disabled system-wide)
        if (    'parent' in self.__plotDisplayLoc
            and self.erl2context['state'].get('system','plots',1)):

            self.__plot = Erl2Plot(plotLoc=self.__plotDisplayLoc,
                                   statsLoc=self.__statsDisplayLoc,
                                   #figsize=(3.166,1.345), # sizing doesn't seem to matter if frame is weighted properly
                                   figsize=(2.500,1.000),
                                   displaySpecs=displaySpecs,
                                   displayData=displayData,
                                   displayDecimals=self.__displayDecimals,
                                   erl2context=self.erl2context,
                                   )

        # begin monitoring the system
        #print (f"{__class__.__name__}: Debug: __init__({self.subSystemType}) calling monitorSystem()")
        self.monitorSystem()

    # figure out what the target variable's current value is
    def getCurrentValue(self):

        # initialize sensor value, time and online status
        v = t = o = None

        # this logic depends on the subSystemType being the same as the sensorType ('temperature', 'pH, 'DO')
        if self.subSystemType in self.__sensors:

            # grab the current sensor value if we can find it
            if (    hasattr(self.__sensors[self.subSystemType],'value')
                and self.__displayParameter in self.__sensors[self.subSystemType].value):
                v = self.__sensors[self.subSystemType].value[self.__displayParameter]

            # check if current value is invalid
            if (   v is None
                or isnan(v)
                or (len(self.__validRange) >= 1 and v < self.__validRange[0])
                or (len(self.__validRange) >= 2 and v > self.__validRange[1])):
                v = None

            # grab the timestamp when the sensor was last updated
            if hasattr(self.__sensors[self.subSystemType],'lastValid'):
                t = self.__sensors[self.subSystemType].lastValid

            # grab the sensor's online status
            if hasattr(self.__sensors[self.subSystemType],'online'):
                o = self.__sensors[self.subSystemType].online

        #print (f"{self.__class__.__name__}: Debug: getCurrentValue() [{v}][{t}][{o}]")

        # return any values found
        return v, t, o

    # detect a change in mode, and enable/disable widgets according to the current mode
    def applyMode(self, loopCount=0):

        #print (f"{__class__.__name__}: Debug: applyMode({self.subSystemType}) called, recursion level [{loopCount}]")

        # first of all: if there's been any change and we're now in controller mode, reapply parent programming
        if self.__ctrlVar.get() == CONTROLLER:
            self.reloadParentProgram(calledFromApply=True)

        # read the current ctrl+mode of the system
        ctrlVar = self.__ctrlVar.get()
        modeVar = self.__modeVar.get()

        # if we still have the already-active mode, disregard
        if (    self.__lastCtrlVar is not None and self.__lastCtrlVar == ctrlVar
            and self.__lastModeVar is not None and self.__lastModeVar == modeVar):
            return

        # enable/disable this subsystem's associated controls as appropriate
        for c in self.__thisTabControls:
            #if self.__controls[c].controlType in ['heater','chiller']:
            #    print (f"{__class__.__name__}: Debug: applyMode({self.subSystemType}) calling setActive({int(ctrlVar==LOCAL and modeVar==MANUAL)}) for [{self.__controls[c].controlType}]")
            self.__controls[c].setActive(int(ctrlVar in [OFFLINE,LOCAL] and modeVar==MANUAL))

        # enable/disable the static setpoint entry field as appropriate
        if self.staticSetpointEntry is not None:
            if ctrlVar==LOCAL and modeVar==AUTO_STATIC:
                self.staticSetpointEntry.setActive(1)
            else:
                self.staticSetpointEntry.setActive(0)

        # enable/disable the hysteresis entry field as appropriate
        if self.__logic == 'hysteresis' and self.hysteresisEntry is not None:
            if ctrlVar==LOCAL and modeVar!=MANUAL:
                self.hysteresisEntry.setActive(1)
            else:
                self.hysteresisEntry.setActive(0)

        # enable/disable the dynamic setpoint entry fields as appropriate
        for w in self.dynamicSetpointsEntry:
            if ctrlVar==LOCAL and modeVar==AUTO_DYNAMIC:
                w.setActive(1)
            else:
                w.setActive(0)

        # for any kind of mode change (either local or controller), reset all hardware controls
        # (exception: don't reset controls if in controller/manual mode)
        if ctrlVar != CONTROLLER or modeVar != MANUAL:
            for c in self.__controls.values():
                c.resetControl()

        # make a note of this change in the logs (unless this is system startup)
        if self.log is not None and self.__lastModeVar is not None:
            self.log.writeMessage(f"mode changed from [{self.__modeDict[self.__lastModeVar]}] to [{self.__modeDict[modeVar]}]")

        # remember the last known mode
        self.__lastCtrlVar = ctrlVar
        self.__lastModeVar = modeVar
        self.__modeChanged = True

        # don't save ctrl or mode values if in Offline mode
        if ctrlVar == OFFLINE:
            pass

        # if in controller mode, just save the ctrlVar to the regular state file
        elif ctrlVar == CONTROLLER:
            self.erl2context['state'].set([(self.subSystemType,'ctrl',ctrlVar)])

        # if in local mode, save ctrlVar and modeVar both
        else:
            self.erl2context['state'].set([(self.subSystemType,'ctrl',ctrlVar),
                                           (self.subSystemType,'mode',modeVar)])

        # save actual ctrl/mode settings so that controller will see them
        self.erl2context['state'].set([(self.subSystemType,'ctrl.actual',ctrlVar),
                                       (self.subSystemType,'mode.actual',modeVar)])

        # update display widgets to show current mode and setpoint
        self.updateDisplays()

        # trigger monitorSystem right away to see immediate effects of mode change
        if loopCount <= 10:
            #print (f"{__class__.__name__}: Debug: applyMode({self.subSystemType}) calling monitorSystem(), recursion level [{loopCount+1}]")
            self.monitorSystem(loopCount+1)

    def updateDisplays(self):

        # read the current mode of the system
        ctrlVar = self.__ctrlVar.get()
        modeVar = self.__modeVar.get()

        # format the setpoint for the display widgets
        upd = f"{float(round(self.__activeSetpoint,self.__displayDecimals)):.{self.__displayDecimals}f}"

        # note that in Manual mode, the setpoint is meaningless
        if modeVar==MANUAL:
            upd = '--'

        # update the setpoint displays
        for w in self.__setpointDisplayWidgets:
            w.config(text=upd)

        # update the mode displays
        #txt = self.__modeDict[modeVar] + ' mode'
        txt = self.__ctrlDict[ctrlVar] + '/' + sub('^Auto ','',self.__modeDict[modeVar])
        for w in self.__modeDisplayWidgets:
            w.config(text=txt)

    def monitorSystem(self, loopCount=0):

        #print (f"{__class__.__name__}: Debug: monitorSystem({self.subSystemType}) called, recursion level [{loopCount}]")

        # figure out by the end if a new data record should be written
        writeNow = False

        # make note of the current timestamp
        currentTime = dt.now(tz=tz.utc)

        # what is the current hour of day? (USE LOCAL TIME!)
        currentHour = int(currentTime.astimezone(self.__timezone).strftime('%H'))

        # read the current mode of the system
        ctrlVar = self.__ctrlVar.get()
        modeVar = self.__modeVar.get()

        # try to get the sensor's current value
        currVal, currTime, currOnline = self.getCurrentValue()

        # if current value is missing or sensor is considered offline
        if (currVal is None or not currOnline):

            # change to Offline/Manual mode if not already there
            if ctrlVar!=OFFLINE or modeVar!=MANUAL:

                # change to Offline/Manual mode
                self.__ctrlVar.set(OFFLINE)
                self.__modeVar.set(MANUAL)
                ctrlVar=OFFLINE
                modeVar=MANUAL

                # trigger a data record to the log
                writeNow = True

                # apply the new mode, but make absolutely certain this isn't an infinite loop
                if loopCount <= 10:
                    #print (f"{__class__.__name__}: Debug: monitorSystem({self.subSystemType}) calling applyMode() while sensor offline, recursion level [{loopCount+1}]")
                    self.applyMode(loopCount+1)

        # contrariwise, if we are currently in offline mode but the sensor is no longer offline
        elif ctrlVar==OFFLINE:

            # call up the last known ctrl setting and return to it
            lastCtrlVar = self.erl2context['state'].get(self.subSystemType,'ctrl',LOCAL)
            self.__ctrlVar.set(lastCtrlVar)
            ctrlVar=lastCtrlVar

            # reload parent program if going back to controller mode
            if lastCtrlVar==CONTROLLER:
                self.reloadParentProgram(calledFromApply=True)

            # otherwise, return to last known local mode
            else:
                lastModeVar = self.erl2context['state'].get(self.subSystemType,'mode',self.__modeDefault)
                self.__modeVar.set(lastModeVar)
                modeVar=lastModeVar

            # trigger a data record to the log
            writeNow = True

            # apply the new mode, but make absolutely certain this isn't an infinite loop
            if loopCount <= 10:
                #print (f"{__class__.__name__}: Debug: monitorSystem({self.subSystemType}) calling applyMode() while sensor BACK ONLINE, recursion level [{loopCount+1}]")
                self.applyMode(loopCount+1)

        # no logic to carry out if in Manual mode
        if modeVar==MANUAL:
            pass

        # static and dynamic modes share some logic
        elif modeVar in [AUTO_STATIC,AUTO_DYNAMIC]:

            # keep track of whether the active setpoint changed
            newSetpoint = None

            # trigger a data record on the hour if in auto static/dynamic mode
            if self.__hour is None or self.__hour != currentHour:
                self.__hour = currentHour
                writeNow = True

            # static setpoint
            if modeVar==AUTO_STATIC:
                newSetpoint = float(self.staticSetpointEntry.stringVar.get())

            # dynamic setpoint
            else:
                # what is the setpoint corresponding to the current hour?
                newSetpoint = float(self.dynamicSetpointsEntry[currentHour].stringVar.get())

            # trigger a data record if the active setpoint changed
            if self.__activeSetpoint is None or self.__activeSetpoint != newSetpoint:
                self.__activeSetpoint = newSetpoint
                self.__setpointLastChanged = currentTime
                writeNow = True

            # hysteresis logic -- these systems have a targeted setpoint, toggles
            # to raise and lower the current value, and a hardcoded parameter for
            # the maximum allowed amount of drift from the setpoint
            if self.__logic == 'hysteresis':

                # what is the hysteresis -- the allowable drift from the targeted setpoint?
                if self.__logic == 'hysteresis' and self.hysteresisEntry is not None:
                    hysteresis = float(self.hysteresisEntry.stringVar.get())
                else:
                    hysteresis = float('nan')

                # fine-tune the logic if recent sensor history can be determined
                currSens = minSens = maxSens = None
                if self.subSystemType in self.__sensors:
                    currSens, _, minSens, maxSens = self.__sensors[self.subSystemType].reportValue() #numIntervals=12)

                # we want to know recent toggle history too
                currRaise = avgRaise = currLower = avgLower = None
                if 'to.raise' in self.__toggles:
                    currRaise, avgRaise, _, _ = self.__toggles['to.raise'].reportValue() #numIntervals=12)
                if 'to.lower' in self.__toggles:
                    currLower, avgLower, _, _ = self.__toggles['to.lower'].reportValue() #numIntervals=12)

                #print (f"{__class__.__name__}: Debug: monitorSystem({self.subSystemType}) " +
                #       f"setpoint [{self.__activeSetpoint}], hysteresis [{hysteresis}], " +
                #       f"minSens [{minSens:.3f}], maxSens [{maxSens:.3f}]")

                # hysteresis default behavior
                lowHyst = highHyst = hysteresis

                # can't do anything without proper information
                if (    currSens is not None and minSens is not None and maxSens is not None
                    and avgRaise is not None and avgLower is not None):

                    # hysteresis concepts:
                    #
                    #  regime: whether pushing hotter ( +1. ) or cooler ( -1. )
                    #  controlOn: last-known state of the dominant control in this regime
                    #  lowerLimit: lower limit of temp since control last kicked on
                    #  upperLimit: upper limit of temp since control last kicked on
                    #  prevHyst: most recently-applied (adjusted) hysteresis
                    #  prevTemp: last known temperature of the system
                    #  currentTime: time of analysis, for potential reloading after reboot

                    # context for hysteresis logic
                    regime = currControl = recentLimit = 0.

                    # heater-only regime
                    if avgLower == 0. and avgRaise > 0.:
                        regime = 1.

                    # chiller-only regime
                    elif avgLower > 0. and avgRaise == 0.:
                        regime = -1.

                    # if both controls are zero and there's a previous regime, reload it
                    elif avgLower == 0. and avgRaise == 0. and 'regime' in self.__hysteresisMetadata:
                        regime = self.__hysteresisMetadata['regime']

                    # no special logic possible, clear out the metadata
                    else:
                        ## debug when changing from nonzero to zero regime
                        #if 'prevHyst' in self.__hysteresisMetadata:
                        #    print (f"{__class__.__name__}: Debug: hysteresis: RESET: " +
                        #           f"avgLower [{avgLower}], " +
                        #           f"avgLower == 0. [{avgLower == 0.}], " +
                        #           f"avgLower > 0. [{avgLower> 0. }], " +
                        #           f"avgRaise [{avgRaise}], " +
                        #           f"avgRaise == 0. [{avgRaise == 0.}], " +
                        #           f"avgRaise > 0. [{avgRaise> 0. }]")

                        for param in ['regime', 'controlOn', 'lowerLimit', 'upperLimit',
                                      'prevHyst', 'prevTemp', 'currentTime']:
                            if param in self.__hysteresisMetadata:
                                del self.__hysteresisMetadata[param]

                    # some additional parameters are set based on regime
                    if regime > 0.:
                        currControl = currRaise
                        recentLimit = maxSens
                    elif regime < 0.:
                        currControl = currLower
                        recentLimit = minSens

                    # remember regime for next time through
                    self.__hysteresisMetadata['regime'] = regime

                    # remember timing, in case system is restarted quickly after shutdown
                    self.__hysteresisMetadata['currentTime'] = currentTime

                    # three options: one, if we are new to the current regime
                    if 'controlOn' not in self.__hysteresisMetadata:

                        # use defaults of (nearest) hysteresis limit...
                        self.__hysteresisMetadata['lowerLimit'] = self.__activeSetpoint + (regime * hysteresis)
                        self.__hysteresisMetadata['upperLimit'] = self.__activeSetpoint + (regime * hysteresis)

                        # ...and adjust for current temp
                        if currSens < self.__hysteresisMetadata['lowerLimit']:
                            self.__hysteresisMetadata['lowerLimit'] = currSens
                        if currSens > self.__hysteresisMetadata['upperLimit']:
                            self.__hysteresisMetadata['upperLimit'] = currSens

                    # two, if the temp control has just kicked on, update logic
                    elif currControl > 0 and self.__hysteresisMetadata['controlOn'] == 0.:

                        # do not approach within 25% of the hysteresis limit to the far side of
                        # the temp range: keep this buffer to avoid unnecessary triggering of
                        # the opposing control (based on last 5min of sensor data). this may
                        # be negative if the temp limits already exceed this boundary

                        farBoundary = self.__activeSetpoint + (regime * 0.75 * hysteresis)
                        buffer = regime * (farBoundary - recentLimit)

                        # shouldn't be possible to reach here without knowing lowerLimit
                        # and upperLimit, but define sensible (conservative) defaults JIC
                        thisLowerLimit = self.__activeSetpoint + (regime * hysteresis)
                        thisUpperLimit = farBoundary
                        if 'lowerLimit' in self.__hysteresisMetadata:
                            thisLowerLimit = self.__hysteresisMetadata['lowerLimit']
                        if 'upperLimit' in self.__hysteresisMetadata:
                            thisUpperLimit = self.__hysteresisMetadata['upperLimit']

                        # the current system midpoint
                        midpoint = (thisLowerLimit + thisUpperLimit) / 2.

                        # hysteresis difference is how much change we want to make to the
                        # system as it is running now (can be -ve, if we're backing off)
                        hystDiff = regime * (self.__activeSetpoint - midpoint)

                        # but we're limited by the buffer in how far we can push
                        hystDiff = min(buffer, hystDiff)

                        # now compare to any known previous hysteresis
                        prevHyst = hysteresis
                        if 'prevHyst' in self.__hysteresisMetadata:
                            prevHyst = self.__hysteresisMetadata['prevHyst']

                        # in this framing, a positive hysteresisDiff means we want to be more
                        # aggressive, i.e., we want to reduce the hysteresis (but we cannot
                        # reduce it to less than zero
                        newHyst = max(0., (prevHyst - hystDiff))

                        # remember hysteresis for use until a new one is calculated
                        self.__hysteresisMetadata['prevHyst'] = newHyst

                        # if prevTemp available, take that into account
                        thisPrevTemp = currSens
                        if 'prevTemp' in self.__hysteresisMetadata:
                            thisPrevTemp = self.__hysteresisMetadata['prevTemp']

                        # start tracking new temp limits for next cycle
                        self.__hysteresisMetadata['lowerLimit'] = min(currSens, thisPrevTemp)
                        self.__hysteresisMetadata['upperLimit'] = max(currSens, thisPrevTemp)

                        #print (f"{__class__.__name__}: Debug: monitorSystem({self.subSystemType}): " +
                        #       f"farBoundary [{farBoundary:6.4f}], buffer [{buffer:6.4f}], midpoint [{midpoint:.4f}], " +
                        #       f"hystDiff [{hystDiff:6.4f}], prevHyst [{prevHyst:6.4f}], newHyst [{newHyst:6.4f}]")

                    # three, the control is off (whether newly- or not), or not-newly on
                    else:

                        # in this case we're just tracking temps during the cycle
                        if (   'lowerLimit' not in self.__hysteresisMetadata
                            or currSens < self.__hysteresisMetadata['lowerLimit']):

                            self.__hysteresisMetadata['lowerLimit'] = currSens

                        if (   'upperLimit' not in self.__hysteresisMetadata
                            or currSens > self.__hysteresisMetadata['upperLimit']):

                            self.__hysteresisMetadata['upperLimit'] = currSens

                    # remember the current control setting, and system temperature
                    self.__hysteresisMetadata['controlOn'] = currControl
                    self.__hysteresisMetadata['prevTemp'] = currSens

                    # finally, save snapshot of metadata to state file
                    self.erl2context['state'].set([(self.subSystemType,'hysteresisMetadata',self.__hysteresisMetadata)])

                # use saved value, if any for adjusted hysteresis
                if 'prevHyst' in self.__hysteresisMetadata:
                    if regime > 0:
                        lowHyst = self.__hysteresisMetadata['prevHyst']
                    elif regime < 0:
                        highHyst = self.__hysteresisMetadata['prevHyst']

                printOn = printLower = printUpper = None
                if 'controlOn' in self.__hysteresisMetadata:
                    printOn = self.__hysteresisMetadata['controlOn']
                if 'lowerLimit' in self.__hysteresisMetadata:
                    printLower = self.__hysteresisMetadata['lowerLimit']
                if 'upperLimit' in self.__hysteresisMetadata:
                    printUpper = self.__hysteresisMetadata['upperLimit']

                #print (f"{__class__.__name__}: Debug: hysteresis: " +
                #       #f"setpoint [{self.__activeSetpoint}], " +
                #       f"regime [{regime:2.0f}], " +
                #       f"LOW hyst [{lowHyst:.4f}], " +
                #       f"HIGH hyst [{highHyst:.4f}], " +
                #       f"controlOn [{printOn:2.0f}], " +
                #       f"currRaise [{currRaise:2.0f}], " +
                #       f"avgRaise [{avgRaise:5.3f}], " +
                #       f"currLower [{currLower:2.0f}], " +
                #       f"avgLower [{avgLower:5.3f}], " +
                #       f"currSens [{currSens:5.3f}], " +
                #       f"minSens [{minSens:5.3f}], " +
                #       f"maxSens [{maxSens:5.3f}], " +
                #       f"recentLim [{recentLimit:5.3f}], " +
                #       f"lowerLim [{printLower:5.3f}], " +
                #       f"upperLim [{printUpper:5.3f}]")

                # determine the correct course of action
                if currVal < self.__activeSetpoint - lowHyst:
                    if 'to.raise' in self.__toggles:
                        self.__toggles['to.raise'].setControl(1.)
                    if 'to.lower' in self.__toggles:
                        self.__toggles['to.lower'].setControl(0.)
                elif currVal > self.__activeSetpoint + highHyst:
                    if 'to.raise' in self.__toggles:
                        self.__toggles['to.raise'].setControl(0.)
                    if 'to.lower' in self.__toggles:
                        self.__toggles['to.lower'].setControl(1.)
                else:
                    if 'to.raise' in self.__toggles:
                        self.__toggles['to.raise'].setControl(0.)
                    if 'to.lower' in self.__toggles:
                        self.__toggles['to.lower'].setControl(0.)

        # unrecognized mode
        else:
            raise SystemError(f"{self.__class__.__name__}: Error: monitorSystem() invalid mode [{modeVar}]")

        # PID logic -- uses the simple_pid library to set the MFCs to gas
        # rates that will raise or lower the current value of the system
        if self.__logic == 'PID':

            # loop through the various types of MFCs
            for mfc in self.__MFCs:

                # sometimes the PID isn't needed
                if (currVal is None or not currOnline or modeVar == MANUAL):

                    # disable the PID if it exists (if it wasn't created yet, then ignore it)
                    if mfc in self.__PIDs and self.__PIDs[mfc].auto_mode:
                        #print (f"{__class__.__name__}: Debug: setting PID auto_mode to False for [{mfc}]")
                        self.__PIDs[mfc].auto_mode = False

                # explicitly check if the system is in auto (static or dynamic) mode
                elif modeVar in [AUTO_STATIC,AUTO_DYNAMIC]:

                    # remember if we've given the PID new instructions
                    newSetpoint = False

                    # create the PID if it doesn't exist yet
                    if mfc not in self.__PIDs:

                        # initialize the new PID object
                        #print (f"{__class__.__name__}: Debug: initializing PID for [{mfc}]")
                        self.__PIDs[mfc] = PID(self.__pidParams[mfc]['Kp'],
                                               self.__pidParams[mfc]['Ki'],
                                               self.__pidParams[mfc]['Kd'])

                        # tell it what the output limits of this MFC are
                        #print (f"{__class__.__name__}: Debug: setting PID limits for [{mfc}] to [{self.__MFCs[mfc].validRange}]")
                        self.__PIDs[mfc].output_limits = self.__MFCs[mfc].validRange

                    # ensure that the PID is enabled
                    if not self.__PIDs[mfc].auto_mode:
                        #print (f"{__class__.__name__}: Debug: setting PID auto_mode to True for [{mfc}]")
                        self.__PIDs[mfc].auto_mode = True

                    # make sure it knows the setpoint we're currently working toward
                    if self.__PIDs[mfc].setpoint != self.__activeSetpoint:
                        #print (f"{__class__.__name__}: Debug: setting PID setpoint to [{self.__activeSetpoint}] for [{mfc}]")
                        self.__PIDs[mfc].setpoint = self.__activeSetpoint
                        newSetpoint = True

                    # don't consult the PID unless the system's current value has been
                    # updated since the last time it was called, or there's a new setpoint
                    if mfc not in self.__pidLastUpdated or self.__pidLastUpdated[mfc] < currTime or newSetpoint:

                        # ask the PID what the new MFC setting should be
                        newSetting = self.__PIDs[mfc](currVal)
                        #print (f"{__class__.__name__}: Debug: PID says flow rate for [{mfc}] should be [{newSetting}], given current system value [{currVal}]")

                        # for now, don't let it go lower than the default minimum
                        vwr = self.__MFCs[mfc].valueWhenReset()
                        if newSetting < vwr:
                            newSetting = vwr

                        # apply that value to the MFC
                        self.__MFCs[mfc].setControl(newSetting=newSetting)

                        # remember the last time we updated the PID
                        self.__pidLastUpdated[mfc] = currTime

        # if offline, then all control buttons are disabled other than Offline
        if ctrlVar==OFFLINE:
            #self.__ctrlRadioWidgets[OFFLINE].config(state='normal')
            self.__ctrlRadioWidgets[LOCAL-1].config(state='disabled')
            self.__ctrlRadioWidgets[CONTROLLER-1].config(state='disabled')

        # otherwise disable Offline and enable Local
        else:
            #self.__ctrlRadioWidgets[OFFLINE].config(state='disabled')
            self.__ctrlRadioWidgets[LOCAL-1].config(state='normal')

            # and Controller button is enabled iff there is a parent program
            if self.hasParentProgram():
                self.__ctrlRadioWidgets[CONTROLLER-1].config(state='normal')
            else:
                self.__ctrlRadioWidgets[CONTROLLER-1].config(state='disabled')

        # if this is controller mode, then all mode buttons should be disabled
        if ctrlVar==CONTROLLER:
            self.__modeRadioWidgets[MANUAL].config(state='disabled')
            self.__modeRadioWidgets[AUTO_STATIC].config(state='disabled')
            self.__modeRadioWidgets[AUTO_DYNAMIC].config(state='disabled')

        # otherwise: sensors come and go, so make sure the setpoint-related
        # mode radio buttons are enabled if-and-only-if the sensor is available
        else:
            if (currVal is not None and currOnline):
                self.__modeRadioWidgets[MANUAL].config(state='normal')
                self.__modeRadioWidgets[AUTO_STATIC].config(state='normal')
                self.__modeRadioWidgets[AUTO_DYNAMIC].config(state='normal')
            else:
                self.__modeRadioWidgets[MANUAL].config(state='normal')
                self.__modeRadioWidgets[AUTO_STATIC].config(state='disabled')
                self.__modeRadioWidgets[AUTO_DYNAMIC].config(state='disabled')

        ## also, disable/enable the offset entry field depending on controller mode
        #if ctrlVar==CONTROLLER: actv = 0
        #else:                   actv = 1
        #for s in self.__sensors.values():
        #    if hasattr(s, 'allEntries'):
        #        for e in s.allEntries:
        #            e.setActive(actv)

        # if the mode has changed, always trigger a data record
        if self.__modeChanged:
            self.__modeChanged = False
            self.__modeLastChanged = currentTime
            writeNow = True

        # write a subsystems data record if needed
        if writeNow:

            # initialize timing attributes if not yet set
            if self.__modeLastChanged is None:
                self.__modeLastChanged = currentTime
            if self.__setpointLastChanged is None:
                self.__setpointLastChanged = currentTime
            if self.__hour is None:
                self.__hour = currentHour

            # write a record to the data file
            self.log.writeData(
                {'Timestamp.UTC': currentTime.strftime(self.__dtFormat),
                 'Timestamp.Local': currentTime.astimezone(self.__timezone).strftime(self.__dtFormat),
                 'Hour.Local': self.__hour,
                 'Control': ctrlVar,
                 'Active Mode': modeVar,
                 'Active Setpoint': self.__activeSetpoint,
                 'Mode Last Changed (Local)': self.__modeLastChanged.astimezone(self.__timezone).strftime(self.__dtFormat),
                 'Septpoint Last Changed (Local)': self.__setpointLastChanged.astimezone(self.__timezone).strftime(self.__dtFormat)}
            )

        # update display widgets to show to current mode and setpoint
        self.updateDisplays()

        # if there's a plot
        if self.__plot is not None:

            # every 60 loops (approx 5 mins) push new data to the plots
            if (self.__plotTracker is None or self.__plotTracker >= 60):
                self.__plot.updatePlot()
                self.__plotTracker = 0
            else:
                self.__plotTracker += 1

        # this parameter is written (to share w/controller) but never read
        # (report None if in Manual mode, which does not use any Setpoint)
        if modeVar == MANUAL:
            self.erl2context['state'].set([(self.subSystemType,'activeSetpoint',None)])
        else:
            self.erl2context['state'].set([(self.subSystemType,'activeSetpoint',self.__activeSetpoint)])

        # wake up every five seconds and see if anything needs adjustment (only is loopCount is 0 though)
        if loopCount == 0:
            #print (f"{__class__.__name__}: Debug: monitorSystem({self.subSystemType}) being scheduled to run again in 5s")
            self.__modeRadioWidgets[0].after(5000, self.monitorSystem)

    # wrapper methods for changeEntry()
    def changeStaticSetpoint(self):
        self.changeEntry('staticSetpoint')
    def changeHysteresis(self):
        self.changeEntry('hysteresis')
    def changeDynamicSetpoint(self,index):
        self.changeEntry('dynamicSetpoints',index)

    def changeEntry(self, param, index=None):

        # if this gets called in OFFLINE or CONTROLLER mode, something is awry
        if self.__ctrlVar.get() in [OFFLINE,CONTROLLER]:
            raise SystemError(f"{self.__class__.__name__}: Error: changeEntry() called while in CONTROLLER mode")

        # dynamically determine the names of attributes we want based on param string
        floatName = param + 'Float'
        entryName = param + 'Entry'

        try:
            # resolve the attribute names into values
            floatFieldOrList = getattr(self,floatName)
            entryFieldOrList = getattr(self,entryName)

            # we want both the float list and the individual value
            if type(floatFieldOrList) is list and index is not None:
                floatValue = floatFieldOrList[index]
                floatList = floatFieldOrList
            else:
                floatValue = floatFieldOrList
                floatList = None

            # for entries we only want the individual entry field
            if type(entryFieldOrList) is list and index is not None:
                entryField = entryFieldOrList[index]
            else:
                entryField = entryFieldOrList

        except Exception as e:
            #print (f"{self.__class__.__name__}: Debug: changeEntry({self.subSystemType}): cannot identify class attributes for [{param}]{'['+str(index)+']' if index is not None else ''}\n[{e}]")
            return

        #print (f"{self.__class__.__name__}: Debug: changeEntry({self.subSystemType},{param}): before [{floatValue}], after [{float(entryField.stringVar.get())}]")

        # check if this represents an actual change in value, or just formatting
        if float(entryField.stringVar.get()) != floatValue:

            #print (f"{self.__class__.__name__}: Debug: changeEntry({self.subSystemType}):"
            #       + f" [{param}]{'['+str(index)+']' if index is not None else ''} change detected:"
            #       + f" before [{floatValue}], after [{float(entryField.stringVar.get())}]")

            # make a note in the log about this change
            if self.log is not None:
                self.log.writeMessage(f"{param}{'['+str(index)+']' if index is not None else ''} value changed from [{floatValue}] to [{float(entryField.stringVar.get())}]")

            # update the entry (float) value
            floatValue = float(entryField.stringVar.get())
            if floatList is not None:
                floatList[index] = floatValue
                setattr(self,floatName,floatList)
            else:
                setattr(self,floatName,floatValue)

            # trigger monitorSystem right away to see immediate effects of mode change
            self.monitorSystem()

            # notify application that its state has changed
            if floatList is not None:
                self.erl2context['state'].set([(self.subSystemType,param,floatList)])
            else:
                self.erl2context['state'].set([(self.subSystemType,param,floatValue)])

    def controlsLog(self, message):

        # nothing to do if logging isn't enabled
        if self.log is not None:

            # only act if this is Manual mode
            if self.__modeVar.get() == MANUAL:

                # send the control's update to the subsystem log
                self.log.writeMessage(message)

    def hasParentProgram(self):

        # assess whether this subsystem has enough details to revert parent programming
        return ('parentState' in self.erl2context
            and self.erl2context['parentState'].isType(self.subSystemType)
            and self.erl2context['parentState'].isName(self.subSystemType, 'mode')
            and (self.__logic != 'hysteresis'
                 or self.erl2context['parentState'].isName(self.subSystemType, 'hysteresis'))
            and self.erl2context['parentState'].isName(self.subSystemType, 'staticSetpoint')
            and self.erl2context['parentState'].isName(self.subSystemType, 'dynamicSetpoints')
            )

    def reloadParentProgram(self, calledFromApply=False):

        # first make sure the parent program is fully defined
        if not self.hasParentProgram():
            raise SystemError(f"{self.__class__.__name__}: Error: reloadParentProgram(): missing program")

        # set local/controller to controller
        #print (f"{self.__class__.__name__}: Debug: reloadParentProgram({self.subSystemType}): "
        #       f"setting ctrlVar to [{CONTROLLER}]")
        self.__ctrlVar.set(CONTROLLER)

        # set mode
        newMode = self.erl2context['parentState'].get(self.subSystemType, 'mode', None)
        #print (f"{self.__class__.__name__}: Debug: reloadParentProgram({self.subSystemType}): setting modeVar to [{newMode}]")
        self.__modeVar.set(newMode)

        # saving this mode allows the Controller to instruct the tank to go into Controller
        # mode, now or later, even if the sensor is Offline and the subSystem was in Local mode
        self.erl2context['state'].set([(self.subSystemType,'ctrl',CONTROLLER),
                                       (self.subSystemType,'ctrl.actual',CONTROLLER),
                                       (self.subSystemType,'mode.actual',newMode)])

        # if the new mode is manual, set the toggle and/or manual controls too
        if newMode == MANUAL:

            # toggle controls (Heater, Chiller)
            if self.erl2context['parentState'].isName(self.subSystemType, 'toggle'):

                # the controls, and the values to apply
                toggleKeys = list(self.__toggles.keys())
                toggleSets = self.erl2context['parentState'].get(self.subSystemType, 'toggle', None)
                assert(len(toggleKeys) == len(toggleSets))

                # one control value for each toggle control
                for ind in range(len(toggleKeys)):
                    #print (f"{self.__class__.__name__}: Debug: reloadParentProgram({self.subSystemType}): "
                    #       f"setting [{self.__toggles[toggleKeys[ind]].controlType}] to [{toggleSets[ind]}]")
                    self.__toggles[toggleKeys[ind]].setControl(toggleSets[ind], force=True)

            # manual controls (MFCs)
            if self.erl2context['parentState'].isName(self.subSystemType, 'manual'):

                # the controls, and the values to apply
                manualKeys = list(self.__MFCs.keys())
                manualSets = self.erl2context['parentState'].get(self.subSystemType, 'manual', None)
                assert(len(manualKeys) == len(manualSets))

                # one control value for each manual control
                for ind in range(len(manualKeys)):
                    self.__MFCs[manualKeys[ind]].setControl(manualSets[ind], force=True)

        # set hysteresis, if applicable
        if self.__logic == 'hysteresis' and self.hysteresisEntry is not None:
            #print (f"{self.__class__.__name__}: Debug: reloadParentProgram({self.subSystemType}): "
            #       f"setting hysteresis to [{self.erl2context['parentState'].get(self.subSystemType, 'hysteresis', None)}]")
            self.hysteresisEntry.setValue(self.erl2context['parentState'].get(self.subSystemType, 'hysteresis', None))
            self.hysteresisFloat = self.hysteresisEntry.floatValue

        # set staticSetpoint
        #print (f"{self.__class__.__name__}: Debug: reloadParentProgram({self.subSystemType}): "
        #       f"setting staticSetpoint to [{self.erl2context['parentState'].get(self.subSystemType, 'staticSetpoint', None)}]")
        self.staticSetpointEntry.setValue(self.erl2context['parentState'].get(self.subSystemType, 'staticSetpoint', None))
        self.staticSetpointFloat = self.staticSetpointEntry.floatValue

        # set dynamicSetpoint
        newVals = self.erl2context['parentState'].get(self.subSystemType, 'dynamicSetpoints', None)

        # we don't expect these lists to be anything but 24 items long
        if len(newVals) != 24 or len(self.dynamicSetpointsFloat) != 24 or len(self.dynamicSetpointsEntry) != 24:
            raise SystemError(f"{self.__class__.__name__}: Error: reloadParentProgram(): unexpected list lengths: "
                              f"newVals [{len(newVals)}], Floats [{len(self.dynamicSetpointsFloat)}], "
                              f"Entries [{len(self.dynamicSetpointsEntry)}], newVals {newVals}")

        #print (f"{self.__class__.__name__}: Debug: reloadParentProgram({self.subSystemType}): "
        #       f"setting dynamicSetpoints to {newVals}")
        for ind in range(len(newVals)):
            self.dynamicSetpointsEntry[ind].setValue(newVals[ind])
            self.dynamicSetpointsFloat[ind] = self.dynamicSetpointsEntry[ind].floatValue

        # mode has changed, so applyMode (unless this method was called from applyMode!)
        if not calledFromApply:
            self.applyMode()

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2SubSystem',font='Arial 30 bold').grid(row=0,column=0,columnspan=4)
    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0,columnspan=4)

    ttk.Label(statusFrame,text='Virtual Temp last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')

    tempFrame = ttk.Frame(root, padding='2', relief='flat', borderwidth=0)
    tempFrame.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')

    radioFrame = ttk.Frame(root, padding='2', relief='flat', borderwidth=0)
    radioFrame.grid(row=1, column=1, padx='2', pady='2', sticky='nesw')

    ctrlRadioFrame = ttk.Frame(radioFrame, padding='2', relief='flat', borderwidth=0)
    ctrlRadioFrame.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')

    modeRadioFrame = ttk.Frame(radioFrame, padding='2', relief='flat', borderwidth=0)
    modeRadioFrame.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')

    controlFrame = ttk.Frame(root, padding='2', relief='flat', borderwidth=0)
    controlFrame.grid(row=1, column=2, padx='2', pady='2', sticky='nesw')

    subSysFrame = ttk.Frame(root, padding='2', relief='flat', borderwidth=0)
    subSysFrame.grid(row=1, column=3, padx='2', pady='2', sticky='nesw')

    dynamicFrame = ttk.Frame(root, padding='2', relief='flat', borderwidth=0)
    dynamicFrame.grid(row=2, column=0, columnspan=4, padx='2', pady='2', sticky='nesw')

    virtualtemp = Erl2VirtualTemp(displayLocs=[{'parent':tempFrame,'row':0,'column':0}],
                                  statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                                  correctionLoc={'parent':subSysFrame,'row':0,'column':0})

    heater = Erl2MegaindOutput(controlType='heater',
                               controlColor='red',
                               displayLocs=[{'parent':controlFrame,'row':0,'column':0}],
                               buttonLoc={'parent':controlFrame,'row':2,'column':0})
    chiller = Erl2MegaindOutput(controlType='chiller',
                                controlColor='blue',
                                displayLocs=[{'parent':controlFrame,'row':1,'column':0}],
                                buttonLoc={'parent':controlFrame,'row':3,'column':0})

    subsystem = Erl2SubSystem(subSystemType='temperature',
                              logic='hysteresis',
                              ctrlRadioLoc={'parent':ctrlRadioFrame,'row':0,'column':0},
                              modeRadioLoc={'parent':modeRadioFrame,'row':0,'column':0},
                              staticSetpointLoc={'parent':subSysFrame,'row':1,'column':0},
                              hysteresisLoc={'parent':subSysFrame,'row':2,'column':0},
                              dynamicSetpointsLoc={'parent':dynamicFrame,'row':0,'column':0},
                              setpointDisplayLocs=[{'parent':tempFrame,'row':1,'column':0}],
                              modeDisplayLocs=[{'parent':tempFrame,'row':2,'column':0}],
                              sensors={'temperature':virtualtemp},
                              toggles={'to.raise':heater,'to.lower':chiller})
    root.mainloop()

if __name__ == "__main__": main()

