#! /usr/bin/python3

from datetime import datetime as dt
from datetime import timezone as tz
import tkinter as tk
from tkinter import ttk
from Erl2Chiller import Erl2Chiller
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Heater import Erl2Heater
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2State import Erl2State
from Erl2VirtualTemp import Erl2VirtualTemp

class Erl2SubSystem():

    def __init__(self,
                 subSystemType='generic',

                 # these controls are unique and aren't cloned to more than one frame
                 radioLoc={},
                 staticSetpointLoc={},
                 hysteresisLoc=None,
                 dynamicSetpointsLoc={},

                 # these displays may be cloned to multiple tabs/frames
                 setpointDisplayLocs=[],
                 modeDisplayLocs=[],

                 radioImages=['radio-off-30.png','radio-on-30.png'],
                 sensors={},
                 controls={},
                 erl2context={}):

        self.subSystemType = subSystemType
        self.__radioLoc = radioLoc
        self.__staticSetpointLoc = staticSetpointLoc
        self.__hysteresisLoc = hysteresisLoc
        self.__dynamicSetpointsLoc = dynamicSetpointsLoc

        self.__setpointDisplayLocs = setpointDisplayLocs
        self.__modeDisplayLocs = modeDisplayLocs

        self.radioImages = radioImages
        self.__sensors = sensors
        self.__controls = controls
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load the associated images; just use the image name as the key
        for i in self.radioImages:
            self.erl2context['img'].addImage(i,i)

        # start a data/log file for the subsystem
        if not self.erl2context['conf']['system']['disableFileLogging']:
            self.log = Erl2Log(logType='subsystem', logName=self.subSystemType, erl2context=self.erl2context)
        else:
            self.log = None

        # borrow the display settings from the sensor config
        self.__displayParameter = self.erl2context['conf'][self.subSystemType]['displayParameter']
        self.__displayDecimals = self.erl2context['conf'][self.subSystemType]['displayDecimals']
        self.__validRange = self.erl2context['conf'][self.subSystemType]['validRange']

        # other useful parameters from Erl2Config
        self.__setpointDefault = self.erl2context['conf'][self.subSystemType]['setpointDefault']
        self.__dynamicDefault = self.erl2context['conf'][self.subSystemType]['dynamicDefault']
        if self.__hysteresisLoc is not None:
            self.__hysteresisDefault = self.erl2context['conf'][self.subSystemType]['hysteresisDefault']

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # also keep a float-valued record of the current values of these parameters
        self.staticSetpointFloat = self.erl2context['state'].get(self.subSystemType,'staticSetpoint',self.__setpointDefault)
        self.dynamicSetpointsFloat = self.erl2context['state'].get(self.subSystemType,'dynamicSetpoints',self.__dynamicDefault)
        if self.__hysteresisLoc is not None:
            self.hysteresisFloat = self.erl2context['state'].get(self.subSystemType,'hysteresis',self.__hysteresisDefault)

        # remember what radio widgets and entry fields are active for this control
        self.__radioWidgets = []
        self.staticSetpointEntry = None
        self.dynamicSetpointsEntry = []
        if self.__hysteresisLoc is not None:
            self.hysteresisEntry = None

        # also keep track of display-only widgets
        self.__setpointDisplayWidgets = []
        self.__modeDisplayWidgets = []

        # remember if this subsystem's associated controls are enabled or not
        self.__controlsEnabled = None

        # the state of this subsystem is described by its mode and active setpoint
        self.__modeVar = tk.IntVar()
        self.__lastModeVar = None
        self.__activeSetpoint = self.__setpointDefault

        # also we track the timing of the subsystem to a certain extent
        self.__hour = None
        self.__modeChanged = False
        self.__modeLastChanged = None
        self.__setpointLastChanged = None

        # and here is the list of all possible modes
        self.__modeDict = {0:'Manual',
                           1:'Child',
                           2:'Auto Static',
                           3:'Auto Dynamic'}

        # during initialization, the default mode is 2 (auto static)
        # (but see if there's a different mode set in the system saved state)
        self.__modeVar.set(self.erl2context['state'].get(self.subSystemType,'mode',2))

        # add radio buttons to control this subsystem's operating mode
        for value , text in self.__modeDict.items():
            r = tk.Radiobutton(self.__radioLoc['parent'],
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
            r.grid(row=value,column=0,ipadx=2,ipady=2,sticky='w')

            self.__radioWidgets.append(r)

        # create the static setpoint entry widget's base frame as a child of its parent
        f = ttk.Frame(self.__staticSetpointLoc['parent'], padding='2 2', relief='solid', borderwidth=0)
        f.grid(row=self.__staticSetpointLoc['row'], column=self.__staticSetpointLoc['column'], padx='2', pady='0', sticky='nwse')

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

        # hysteresis is only used in certain subsystems
        if self.__hysteresisLoc is not None:

            # create the hysteresis entry widget's base frame as a child of its parent
            f = ttk.Frame(self.__hysteresisLoc['parent'], padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=self.__hysteresisLoc['row'], column=self.__hysteresisLoc['column'], padx='2', pady='0', sticky='nwse')

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

        # add dynamic setpoint entry fields

        # create the dynamic setpoint grid's base frame as a child of its parent
        f = ttk.Frame(self.__dynamicSetpointsLoc['parent'], padding='2 2', relief='solid', borderwidth=0)
        f.grid(row=self.__dynamicSetpointsLoc['row'], column=self.__dynamicSetpointsLoc['column'], padx='2', pady='2', sticky='nwse')

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

        # loop through the list of needed setpoint display widgets for this sensor
        for loc in self.__setpointDisplayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text=self.__activeSetpoint, font='Arial 20')
            l.grid(row=0, column=0, sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)

            # keep a list of setpoint display widgets for this sensor
            self.__setpointDisplayWidgets.append(l)

        # loop through the list of needed mode display widgets for this sensor
        for loc in self.__modeDisplayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text=self.__modeDict[self.__modeVar.get()] + ' mode', font='Arial 10 bold italic')
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

        # set the focus to the first radio button
        self.__radioWidgets[0].focus()

        # begin monitoring the system
        self.monitorSystem()

    # testing how manipulating one control can en/disable another
    def applyMode(self):

        # read the current mode of the system
        var = self.__modeVar.get()

        # work in progress: pH and DO subsystems can only do Manual mode for now
        if self.subSystemType != 'temperature':
            var = 0
            for r in range(1,len(self.__radioWidgets)):
                self.__radioWidgets[r].config(state='disabled')

        # if we've just re-clicked the already-active mode, disregard
        if self.__lastModeVar is not None and self.__lastModeVar == var:
            return

        # enable/disable this subsystem's associated controls as appropriate
        for c in self.__controls.values():
            c.setActive(int(var==0))

        # enable/disable the static setpoint entry field as appropriate
        if self.staticSetpointEntry is not None:
            if var==2:
                self.staticSetpointEntry.setActive(1)
            else:
                self.staticSetpointEntry.setActive(0)

        # enable/disable the hysteresis entry field as appropriate
        if self.__hysteresisLoc is not None and self.hysteresisEntry is not None:
            if var!=0:
                self.hysteresisEntry.setActive(1)
            else:
                self.hysteresisEntry.setActive(0)

        # enable/disable the dynamic setpoint entry fields as appropriate
        for w in self.dynamicSetpointsEntry:
            if var==3:
                w.setActive(1)
            else:
                w.setActive(0)

        # if in Manual mode, force all hardware controls to off
        if var==0:
            for c in self.__controls.values():
                c.setControl(0)

        # disable "Child" mode for now
        self.__radioWidgets[1].config(state='disabled')

        # make a note of this change in the logs (unless this is system startup)
        if self.log is not None and self.__lastModeVar is not None:
            self.log.writeMessage(f"mode changed from [{self.__modeDict[self.__lastModeVar]}] to [{self.__modeDict[var]}]")

        # remember the last known mode
        self.__lastModeVar = var
        self.__modeChanged = True

        # save the new mode setting to system state
        self.erl2context['state'].set(self.subSystemType,'mode',var)

        # update display widgets to show to current mode and setpoint
        self.updateDisplays()

        # trigger monitorSystem right away to see immediate effects of mode change
        self.monitorSystem(fromApplyMode=True)

    def updateDisplays(self):

        # read the current mode of the system
        var = self.__modeVar.get()

        # format the setpoint for the display widgets
        upd = f"{float(round(self.__activeSetpoint,self.__displayDecimals)):.{self.__displayDecimals}f}"

        # note that in Manual mode, the setpoint is meaningless
        if var==0:
            upd = '--'

        # update the setpoint displays
        for w in self.__setpointDisplayWidgets:
            w.config(text=upd)

        # update the mode displays
        for w in self.__modeDisplayWidgets:
            w.config(text=self.__modeDict[var] + ' mode')

    def monitorSystem(self, fromApplyMode=False):

        # figure out by the end if a new data record should be written
        writeNow = False

        # make note of the current timestamp
        currentTime = dt.now(tz=tz.utc)

        # what is the current hour of day?
        currentHour = int(currentTime.strftime('%H'))

        # read the current mode of the system
        var = self.__modeVar.get()

        # try to get the current temperature
        if (    'temperature' in self.__sensors
            and hasattr(self.__sensors['temperature'],'value')
            and self.__displayParameter in self.__sensors['temperature'].value):
            temp = self.__sensors['temperature'].value[self.__displayParameter]

        # if temperature is missing
        else:
            # change to Manual mode if not already there
            if var>0:
                # make absolutely certain this isn't an infinite loop
                if not fromApplyMode:
                    self.__modeVar.set(0)
                    self.applyMode()
                    var=0
                    writeNow = True

        # no logic to carry out if in Manual mode
        if var==0:
            pass

        # child mode isn't coded yet
        elif var==1:
            raise SystemError(f"{self.__class__.__name__}: Error: monitorSystem() in [{var}][{self.__modeDict[var]}] mode which is not yet implemented")

        # static and dynamic modes share some logic
        elif var in [2,3]:

            # keep track of whether the active setpoint changed
            newSetpoint = None

            # trigger a data record on the hour if in auto static/dynamic mode
            if self.__hour is None or self.__hour != currentHour:
                self.__hour = currentHour
                writeNow = True

            # static setpoint
            if var==2:
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

            # what is the current temperature?
            if (    'temperature' in self.__sensors
                and hasattr(self.__sensors['temperature'],'value')
                and self.__displayParameter in self.__sensors['temperature'].value):
                temp = self.__sensors['temperature'].value[self.__displayParameter]
            else:
                temp = float('nan')

            # what is the hysteresis -- the allowable drift from the targeted setpoint?
            if self.__hysteresisLoc is not None and self.hysteresisEntry is not None:
                hysteresis = float(self.hysteresisEntry.stringVar.get())
            else:
                hysteresis = float('nan')

            # determine the correct course of action
            if temp < self.__activeSetpoint-hysteresis:
                if 'heater' in self.__controls:
                    self.__controls['heater'].setControl(1)
                if 'chiller' in self.__controls:
                    self.__controls['chiller'].setControl(0)
            elif temp > self.__activeSetpoint+hysteresis:
                if 'heater' in self.__controls:
                    self.__controls['heater'].setControl(0)
                if 'chiller' in self.__controls:
                    self.__controls['chiller'].setControl(1)
            else:
                if 'heater' in self.__controls:
                    self.__controls['heater'].setControl(0)
                if 'chiller' in self.__controls:
                    self.__controls['chiller'].setControl(0)

            #print(f"{self.__class__.__name__}: Debug: mode [{self.__modeDict[var]}], hour [{currentHour}], active setpoint [{self.__activeSetpoint}], hysteresis [{hysteresis}] temp [{temp}]")

        # unrecognized mode
        else:
            raise SystemError(f"{self.__class__.__name__}: Error: monitorSystem() invalid mode [{var}]")

        # temperature sensors come and go, so make sure the setpoint-related
        # radio buttons are enabled if-and-only-if temperature is available
        if (        'temperature' in self.__sensors
                and hasattr(self.__sensors['temperature'],'online')
                and self.__sensors['temperature'].online
                and hasattr(self.__sensors['temperature'],'value')
                and self.__displayParameter in self.__sensors['temperature'].value):
            self.__radioWidgets[2].config(state='normal')
            self.__radioWidgets[3].config(state='normal')
        else:
            self.__radioWidgets[2].config(state='disabled')
            self.__radioWidgets[3].config(state='disabled')

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
                 'Active Mode': var,
                 'Active Setpoint': self.__activeSetpoint,
                 'Mode Last Changed (Local)': self.__modeLastChanged.astimezone(self.__timezone).strftime(self.__dtFormat),
                 'Septpoint Last Changed (Local)': self.__setpointLastChanged.astimezone(self.__timezone).strftime(self.__dtFormat)}
            )

        # update display widgets to show to current mode and setpoint
        self.updateDisplays()

        # wake up every five seconds and see if anything needs adjustment
        self.__radioWidgets[0].after(5000, self.monitorSystem)

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
            self.monitorSystem(fromApplyMode=True)

            # notify application that its state has changed
            if floatList is not None:
                self.erl2context['state'].set(self.subSystemType,param,floatList)
            else:
                self.erl2context['state'].set(self.subSystemType,param,floatValue)

    def controlsLog(self, message):

        # nothing to do if logging isn't enabled
        if self.log is not None:

            # only act if this is Manual mode
            if self.__modeVar.get() == 0:

                # send the control's update to the subsystem log
                self.log.writeMessage(message)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2SubSystem',font='Arial 30 bold').grid(row=0,column=0,columnspan=4)
    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0,columnspan=4)

    ttk.Label(statusFrame,text='Virtual Temp last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nse')

    tempFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    tempFrame.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')

    radioFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    radioFrame.grid(row=1, column=1, padx='2', pady='2', sticky='nesw')

    controlFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    controlFrame.grid(row=1, column=2, padx='2', pady='2', sticky='nesw')

    subSysFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    subSysFrame.grid(row=1, column=3, padx='2', pady='2', sticky='nesw')

    dynamicFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    dynamicFrame.grid(row=2, column=0, columnspan=4, padx='2', pady='2', sticky='nesw')

    virtualtemp = Erl2VirtualTemp(displayLocs=[{'parent':tempFrame,'row':0,'column':0}],
                                  statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                                  correctionLoc={'parent':subSysFrame,'row':0,'column':0})

    heater = Erl2Heater(displayLocs=[{'parent':controlFrame,'row':1,'column':0}],
                        buttonLoc={'parent':controlFrame,'row':3,'column':0})
    chiller = Erl2Chiller(displayLocs=[{'parent':controlFrame,'row':2,'column':0}],
                          buttonLoc={'parent':controlFrame,'row':4,'column':0})

    subsystem = Erl2SubSystem(subSystemType='temperature',
                              radioLoc={'parent':radioFrame,'row':0,'column':0},
                              staticSetpointLoc={'parent':subSysFrame,'row':1,'column':0},
                              hysteresisLoc={'parent':subSysFrame,'row':2,'column':0},
                              dynamicSetpointsLoc={'parent':dynamicFrame,'row':0,'column':0},
                              setpointDisplayLocs=[{'parent':tempFrame,'row':1,'column':0}],
                              modeDisplayLocs=[{'parent':tempFrame,'row':2,'column':0}],
                              sensors={'temperature':virtualtemp},
                              controls={'heater':heater,'chiller':chiller})
    root.mainloop()

if __name__ == "__main__": main()

