from datetime import datetime as dt
from datetime import timezone as tz
from math import isnan
from re import sub
from simple_pid import PID
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2Plot import Erl2Plot
from Erl2PwmOutput import Erl2PwmOutput
from Erl2State import Erl2State
from Erl2VirtualTemp import Erl2VirtualTemp

# control constants
LOCAL=0
CONTROLLER=1

# mode constants
MANUAL=0
AUTO_STATIC=1
AUTO_DYNAMIC=2

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
        self.__controls = {**toggles, **MFCs}
        self.__PIDs = {}
        self.__pidParams = {}
        self.__pidLastUpdated = {}
        self.erl2context = erl2context

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
        self.__setpointDefault = self.erl2context['conf'][self.subSystemType]['setpointDefault']
        self.__dynamicDefault = self.erl2context['conf'][self.subSystemType]['dynamicDefault']
        if self.__logic == 'hysteresis':
            self.__hysteresisDefault = self.erl2context['conf'][self.subSystemType]['hysteresisDefault']

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
        if self.__logic == 'hysteresis':
            self.hysteresisFloat = self.erl2context['state'].get(self.subSystemType,'hysteresis',self.__hysteresisDefault)

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
        self.__ctrlDict = {LOCAL:'Local',
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
                r = tk.Radiobutton(self.__ctrlRadioLoc['parent'],
                                   indicatoron=0,
                                   image=self.erl2context['img'][self.radioImages[0]],
                                   selectimage=self.erl2context['img'][self.radioImages[1]],
                                   compound='left',
                                   font='Arial 16',
                                   bd=0,
                                   highlightthickness=0,
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

        # during initialization, the default is auto static mode
        # (but see if there's a different setting in the system saved state)
        self.__modeVar.set(self.erl2context['state'].get(self.subSystemType,'mode',AUTO_STATIC))

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
                                                 width=4,
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
                                             width=4,
                                             displayDecimals=self.__displayDecimals,
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

        # draw a plot of the history of the subsystem
        if 'parent' in self.__plotDisplayLoc:
            self.__plot = Erl2Plot(plotLoc=self.__plotDisplayLoc,
                                   statsLoc=self.__statsDisplayLoc,
                                   #figsize=(3.166,1.345), # sizing doesn't seem to matter if frame is weighted properly
                                   figsize=(2.500,1.000),
                                   displaySpecs=displaySpecs,
                                   displayData=displayData,
                                   displayDecimals=self.__displayDecimals,
                                   erl2context=self.erl2context)

        # begin monitoring the system
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

        # read the current mode of the system
        ctrlVar = self.__ctrlVar.get()
        modeVar = self.__modeVar.get()

        # if we've just re-clicked the already-active mode, disregard
        if (    self.__lastCtrlVar is not None and self.__lastCtrlVar == ctrlVar
            and self.__lastModeVar is not None and self.__lastModeVar == modeVar):
            return

        # enable/disable this subsystem's associated controls as appropriate
        for c in self.__controls.values():
            #print (f"{__class__.__name__}: Debug: applyMode({self.subSystemType}) calling setActive({int(crtlVar==LOCAL and modeVar==MANUAL)}) for [{c.controlType}]")
            c.setActive(int(ctrlVar==LOCAL and modeVar==MANUAL))

        # special case: if we are leaving Manual mode, reset all MFCs to zero
        for m in self.__MFCs.values():
            m.setControl(newSetting=0.)

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

        # if in Manual mode (either local or controller), reset all hardware controls to off
        if modeVar==MANUAL:
            for c in self.__controls.values():
                c.setControl(0)

        # disable "Controller" mode for now
        #self.__ctrlRadioWidgets[CONTROLLER].config(state='disabled')

        # make a note of this change in the logs (unless this is system startup)
        if self.log is not None and self.__lastModeVar is not None:
            self.log.writeMessage(f"mode changed from [{self.__modeDict[self.__lastModeVar]}] to [{self.__modeDict[modeVar]}]")

        # remember the last known mode
        self.__lastCtrlVar = ctrlVar
        self.__lastModeVar = modeVar
        self.__modeChanged = True

        # save the new mode setting to system state
        self.erl2context['state'].set([(self.subSystemType,'ctrl',ctrlVar),
                                       (self.subSystemType,'mode',modeVar)])

        # update display widgets to show to current mode and setpoint
        self.updateDisplays()

        # trigger monitorSystem right away to see immediate effects of mode change
        if loopCount <= 10:
            #print (f"{__class__.__name__}: Debug: applyMode() recursion level [{loopCount}]")
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

        # figure out by the end if a new data record should be written
        writeNow = False

        # make note of the current timestamp
        currentTime = dt.now(tz=tz.utc)

        # what is the current hour of day?
        currentHour = int(currentTime.strftime('%H'))

        # read the current mode of the system
        ctrlVar = self.__ctrlVar.get()
        modeVar = self.__modeVar.get()

        # try to get the sensor's current value
        currVal, currTime, currOnline = self.getCurrentValue()

        # if current value is missing or invalid
        if (currVal is None):

            # change to Manual mode if not already there
            if modeVar!=MANUAL:

                # change to Manual mode and trigger a data record to the log
                self.__modeVar.set(MANUAL)
                modeVar=MANUAL
                writeNow = True

                # apply the new mode, but make absolutely certain this isn't an infinite loop
                if loopCount <= 10:
                    #print (f"{__class__.__name__}: Debug: monitorSystem() recursion level [{loopCount}]")
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

                #print (f"{__class__.__name__}: Debug: monitorSystem() modeVar is [{modeVar}], currVal is [{currVal}], setpoint is [{self.__activeSetpoint}], hysteresis is [{hysteresis}]")

                # determine the correct course of action
                if currVal < self.__activeSetpoint-hysteresis:
                    if 'to.raise' in self.__toggles:
                        self.__toggles['to.raise'].setControl(1)
                    if 'to.lower' in self.__toggles:
                        self.__toggles['to.lower'].setControl(0)
                elif currVal > self.__activeSetpoint+hysteresis:
                    if 'to.raise' in self.__toggles:
                        self.__toggles['to.raise'].setControl(0)
                    if 'to.lower' in self.__toggles:
                        self.__toggles['to.lower'].setControl(1)
                else:
                    if 'to.raise' in self.__toggles:
                        self.__toggles['to.raise'].setControl(0)
                    if 'to.lower' in self.__toggles:
                        self.__toggles['to.lower'].setControl(0)

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
                        #print (f"{__class__.__name__}: Debug: setting PID limits for [{mfc}] to [{self.__MFCs[mfc].flowRateRange}]")
                        self.__PIDs[mfc].output_limits = self.__MFCs[mfc].flowRateRange

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

                        # apply that value to the MFC
                        self.__MFCs[mfc].setControl(newSetting=newSetting)

                        # remember the last time we updated the PID
                        self.__pidLastUpdated[mfc] = currTime

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

        # also, disable/enable the offset entry field depending on controller mode
        if ctrlVar==CONTROLLER: actv = 0
        else:                   actv = 1
        for s in self.__sensors.values():
            if hasattr(s, 'allEntries'):
                for e in s.allEntries:
                    e.setActive(actv)

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

        # wake up every five seconds and see if anything needs adjustment
        self.__modeRadioWidgets[0].after(5000, self.monitorSystem)

    # wrapper methods for changeEntry()
    def changeStaticSetpoint(self):
        self.changeEntry('staticSetpoint')
    def changeHysteresis(self):
        self.changeEntry('hysteresis')
    def changeDynamicSetpoint(self,index):
        self.changeEntry('dynamicSetpoints',index)

    def changeEntry(self, param, index=None):

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

    heater = Erl2PwmOutput(controlType='heater',
                           controlColor='red',
                           displayLocs=[{'parent':controlFrame,'row':0,'column':0}],
                           buttonLoc={'parent':controlFrame,'row':2,'column':0})
    chiller = Erl2PwmOutput(controlType='chiller',
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

