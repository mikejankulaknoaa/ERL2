from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2State import Erl2State
from Erl2Useful import locDefaults, nextIntervalTime

class Erl2Control():

    def __init__(self,
                 controlType='generic',
                 widgetType='button', # or 'entry'
                 widgetLoc={},
                 displayLocs=[],
                 displayImages=[],
                 buttonImages=[],
                 label='Generic',
                 erl2context={}):

        self.controlType = controlType
        self.__widgetType = widgetType
        self.__widgetLoc = widgetLoc
        self.__displayLocs = displayLocs
        self.displayImages = displayImages
        self.buttonImages = buttonImages
        self.__label = label
        self.erl2context = erl2context

        # something is wrong here if we don't recognize widgetType
        assert(self.__widgetType in ('button','entry'))

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # keep a list of entry widgets
        self.allEntries = []

        # placeholder for this control to be told what subsystem it's part of
        self.subSystem = None

        # remember what widgets are active for this control
        self.__displayWidgets = []
        self.__controlWidget = None
        self.__controlLabelWidget = None

        # and whether the control is allowed to be active or not
        self.enabled = 0

        # for a control, we track setting and history
        self.setting = 0.
        self.settingLastChanged = self.erl2context['state'].get(self.controlType,'lastChanged',None)
        self.offSeconds = []
        self.onSeconds = []
        self.numChanges = 0

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read these useful parameters from Erl2Config
        self.__loggingFrequency = self.erl2context['conf'][self.controlType]['loggingFrequency']
        self.__systemFrequency = self.erl2context['conf']['system']['loggingFrequency']

        # a record of recent control settings for running averages
        self.recentValues = []

        # some controls care about how many decimals are displayed
        self.__displayDecimals = 0
        if 'displayDecimals' in self.erl2context['conf'][self.controlType]:
            self.__displayDecimals = self.erl2context['conf'][self.controlType]['displayDecimals']

        # are there hardware-driven upper+lower limits to this control's value?
        self.controlRange = [0.,1.]
        if 'flowRateRange' in self.erl2context['conf'][self.controlType]:
            self.controlRange = self.erl2context['conf'][self.controlType]['flowRateRange']

        # if necessary, create an object to hold/remember button image objects
        if self.__widgetType == 'button':
            if 'img' not in self.erl2context:
                self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

            # load the associated images; just use the image name as the key
            for i in self.displayImages + self.buttonImages:
                self.erl2context['img'].addImage(i,i)

        # start a data/log file for the control
        self.log = Erl2Log(logType='control', logName=self.controlType, erl2context=self.erl2context)

        # location defaults for control module
        self.modDefaults={'relief':'flat', 'borderwidth':0, 'padx':'2', 'pady':'0'}

        # loop through the list of needed display widgets for this control
        for widgetLoc in self.__displayLocs:

            # interpret loc in terms of system and module .grid() defaults
            loc = locDefaults(widgetLoc, modDefaults=self.modDefaults)

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
            f.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                   padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])

            # a button-type control gets image-type displays
            if self.__widgetType == 'button':

                # add a Label widget to show the current control setting
                l = ttk.Label(f, image=self.erl2context['img'][self.displayImages[0]]
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=1, padx='2 2', sticky='e')

                # this is the (text) Label shown beside the (image) display widget
                ttk.Label(f, text=self.__label, font='Arial 16'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, padx='2 2', sticky='w')

                f.rowconfigure(0,weight=1)
                f.columnconfigure(1,weight=1)
                f.columnconfigure(0,weight=0)

            # an entry-type control gets text-type displays
            elif self.__widgetType == 'entry':

                # add a Label widget to show the current control setting
                l = ttk.Label(f, text=f"{float(round(self.setting,self.__displayDecimals)):.{self.__displayDecimals}f}", font='Arial 8', justify='right'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=1, padx='2', pady='0', sticky='e')

                # this is the (text) Label shown beside the (text) display widget
                ttk.Label(f, text='Setting', font='Arial 8'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, padx='2', pady='0', sticky='w')

                f.rowconfigure(0,weight=1)
                f.columnconfigure(0,weight=1,minsize=45)
                f.columnconfigure(1,weight=1,minsize=76)

            # keep a list of display widgets for this control
            self.__displayWidgets.append(l)

        # interpret loc in terms of system and module .grid() defaults
        loc = locDefaults(self.__widgetLoc, modDefaults=self.modDefaults)

        # create the control widget's base frame as a child of its parent
        f = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        f.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
               padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])

        # create a ttk button control
        if self.__widgetType == 'button':

            # add a button widget to change the setting of the control
            b = tk.Button(f,
                          image=self.erl2context['img'][self.buttonImages[0]],
                          height=40,
                          width=40,
                          bd=0,
                          highlightthickness=0,
                          activebackground='#DBDBDB',
                          command=self.toggleSetting)
            b.grid(row=0, column=0, padx='2 2', sticky='w')

            # this is the (text) Label shown beside the (image) button widget
            l = ttk.Label(f, text=self.__label, font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', self.toggleSetting)

            # keep track of control + label widgets for this control
            self.__controlWidget = b
            self.__controlLabelWidget = l

        # create an erl2 entry control
        elif self.__widgetType == 'entry':

            # add an entry widget to change the current setting of the control
            e = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                          labelLoc={'parent':f,'row':0,'column':0},
                          label=self.__label,
                          width=5,
                          labelFont='Arial 16',
                          displayDecimals=self.__displayDecimals,
                          validRange=self.controlRange,
                          initValue=self.setting,
                          onChange=self.applySetting,
                          erl2context=self.erl2context)

            # expose a list of all entry fields so it can be seen by other modules
            self.allEntries.append(e)

            # keep track of the control widget for this control
            self.__controlWidget = e

        f.rowconfigure(0,weight=1)
        f.columnconfigure(0,weight=0)
        f.columnconfigure(1,weight=1)

        # now set each control's enabled setting individually
        self.setActive(self.enabled)

        # at initialization, force the hardware control to match the logical control setting
        self.setControl(self.setting,force=True)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Control or a child class)
        if self.__class__.__name__ == 'Erl2Control':
            self.updateLog()

    def updateLog(self):

        # remember the timestamp at the exact moment of logging
        currentTime = dt.now(tz=tz.utc)

        #print (f"{self.__class__.__name__}: Debug: updateLog() called [{str(currentTime)}]")

        # did we just start up?
        if self.settingLastChanged is None:
            timing = 0
            self.settingLastChanged = currentTime
            self.erl2context['state'].set([(self.controlType,'setting',self.setting),
                                           (self.controlType,'lastChanged',self.settingLastChanged)])

        # otherwise calculate how long has the system been at its current setting
        # (limited to the current logging interval)
        else:
            timing = currentTime.timestamp() - self.settingLastChanged.timestamp()
            timing = min(timing, self.__loggingFrequency)

        # add up on+off times, then reset them
        onTime = sum(self.onSeconds)
        self.onSeconds = []
        offTime = sum(self.offSeconds)
        self.offSeconds = []

        # remember the number of setting changes, then reset those too
        changes = self.numChanges
        self.numChanges = 0

        # include current timing as appropriate
        if self.setting > 0.:
            onTime += timing
        else:
            offTime += timing

        # calculate current, average setting for this reporting period
        _, avgValue = self.reportValue()

        # if we've passed the next file-writing interval time, write it
        if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

            # create a dict of values we want to log
            m = {'Timestamp.UTC': currentTime.strftime(self.erl2context['conf']['system']['dtFormat']),
                 'Timestamp.Local': currentTime.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']),
                 'Current Setting': self.setting,
                 'Average Setting': avgValue,
                 'Off (seconds)': offTime,
                 'On (seconds)': onTime,
                 'Setting Changes (count)':changes,
                 'Setting Last Changed (Local)': self.settingLastChanged.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat'])}

            # send the new sensor data to the log (in dictionary form)
            if self.log is not None:
                self.log.writeData(m)

        # if the next file-writing interval time is empty or in the past, update it
        if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
            self.__nextFileTime = nextIntervalTime(currentTime, self.__loggingFrequency)

        # when should this method be called next? (milliseconds)
        delay = int((self.__nextFileTime - currentTime.timestamp())*1000)

        # update the display widget(s) again after waiting an appropriate number of milliseconds
        self.__displayWidgets[0].after(delay, self.updateLog)

        #print (f"{self.__class__.__name__}: Debug: updateLog() to be called again after [{float(delay)/1000.}] seconds")

    def setActive(self, enabled=1):

        # remember if controls are enabled or not
        self.enabled = enabled

        # this is how you enable/disable a ttk button
        if self.__widgetType == 'button':

            # only applies if there is a control widget defined
            if self.__controlWidget is not None:

                # update the button control's enabled state
                if self.enabled:
                    self.__controlWidget.config(state='normal')
                else:
                    self.__controlWidget.config(state='disabled')

            # button controls may also have a clickable label
            if self.__controlLabelWidget is not None:

                # update the label's event binding
                if self.enabled:
                    self.__controlLabelWidget.bind('<Button-1>', self.toggleSetting)
                else:
                    self.__controlLabelWidget.unbind('<Button-1>')

        # this is how you enable/disable an erl2 entry
        elif self.__widgetType == 'entry':

            # only applies if there is a control widget defined
            if self.__controlWidget is not None:

                # update the entry control's enabled state
                if self.enabled:
                    self.__controlWidget.setActive(1)
                else:
                    self.__controlWidget.setActive(0)

        # grey out the control widget's label if disabled
        if self.__controlLabelWidget is not None:
            clr = '' # default text color
            if not self.enabled:
                clr = 'grey'
            self.__controlLabelWidget.config(foreground=clr)

        # if we are enabling this control, then make sure that the current
        # hardware setting matches what the control currently shows
        if self.enabled:
            self.applySetting()

    def updateDisplays(self, displayWidgets, controlWidget=None):

        # for a button, apply the appropriate image to all (image) display widgets
        if self.__widgetType == 'button':

            # loop through all placements of this control's display widgets
            for w in displayWidgets:

                # update the display
                w.config(image=self.erl2context['img'][self.displayImages[int(self.setting)]])

            # also change the image on this control's button widget
            if controlWidget is not None:

                # for a button to diplay the 'on' image, two things are required:
                # the control must be set to 'on', and the button must be enabled
                imageInd = self.enabled * self.setting

                # update the button
                controlWidget.config(image=self.erl2context['img'][self.buttonImages[int(imageInd)]])

        # for an entry, format the setting and update all (text) display widgets
        elif self.__widgetType == 'entry':

            # format the values to be displayed
            setting = f"{float(round(self.setting,self.__displayDecimals)):.{self.__displayDecimals}f}"

            # make sure the same value shows in the entry field (e.g. if set by PID logic)
            self.__controlWidget.stringVar.set(setting)

            # loop through all placements of this control's setting display widgets
            for w in displayWidgets:

                # update the setting display
                w.config(text=setting)

    def toggleSetting(self, event=None):

        # something's wrong if this isn't a button-type control
        assert(self.__widgetType == 'button')

        # the new setting is the inverse of the current setting
        self.setControl(1. - self.setting)

        # apply the new setting
        self.applySetting()

    def applySetting(self, event=None):

        # for a button, the new setting (if changing) was already set by toggleSetting
        if self.__widgetType == 'button':
            self.setControl(self.setting)

        # for an entry, the new setting is whatever was entered
        elif self.__widgetType == 'entry':

            # pull new control setting from entry field and apply it
            self.setControl(float(self.__controlWidget.stringVar.get()))

        # if this control has a subsystem, notify it of this change
        if self.subSystem is not None:

            # the subsystem will only log this change if it's made in Manual mode
            self.subSystem.controlsLog(f"{self.controlType} setting was manually changed to {self.setting}")

    def setControl(self, newSetting=0., force=False):

        #print (f"{__class__.__name__}: Debug: setControl({newSetting}) called for [{self.controlType}], force [{force}]")

        # allow changes to be 'forced' even if setting looks the same, but don't log it
        logThis = True
        if self.setting == float(newSetting):
            if not force:
                return
            else:
                logThis = False

        # it's an error to try to set an MFC to a value outside its range
        assert self.controlRange[0] <= float(newSetting) <= self.controlRange[1]

        # tally up how many times the setting is changing
        self.numChanges += 1

        # make note of previous setting, and remember what the current setting is
        previousSetting = self.setting
        self.setting = float(newSetting)

        # apply the new setting to the control's hardware
        self.changeHardwareSetting()

        # remember the time that the setting was changed
        currentTime = dt.now(tz=tz.utc)

        # default the last-changed time to now if it hasn't already been set
        if self.settingLastChanged is None:
            self.settingLastChanged = currentTime

        # keep a record of recent control setting values
        self.recentValues.append({'ts':currentTime, 'prev':previousSetting, 'curr':self.setting})

        # recent values that have gotten too old
        tooOld = currentTime - td(seconds=max(self.__loggingFrequency,self.__systemFrequency))
        self.recentValues = [ x for x in self.recentValues if x['ts'] > tooOld ]

        # calculate how long the system had been at its prior setting
        # (but don't count earlier than the start of the current interval)
        fromTime = self.settingLastChanged.timestamp()
        if self.__nextFileTime is not None and self.__nextFileTime - self.__loggingFrequency > fromTime:
            fromTime = self.__nextFileTime - self.__loggingFrequency
        timing = currentTime.timestamp() - fromTime

        # add this timing to the tally of cumulative off/on time
        if previousSetting > 0.:
            self.onSeconds.append(timing)
        else:
            self.offSeconds.append(timing)

        # save the new last-changed time
        self.settingLastChanged = currentTime

        # some situations do, or do not, trigger log messages
        if logThis:

            # make a note in the control's own log about this change
            if self.log is not None:
                self.log.writeMessage(f"setting changed from [{previousSetting}] to [{self.setting}]")

            # if this control has a subsystem, notify it of this change
            if self.subSystem is not None:

                # the subsystem will only log this change if it's made in Manual mode
                self.subSystem.controlsLog(f"{self.controlType} setting was manually changed from [{previousSetting}] to [{self.setting}]")

        # redraw the app's displays immediately (unless in shutdown)
        if not self.erl2context['conf']['system']['shutdown']:
            if self.__widgetType == 'button':
                self.updateDisplays(self.__displayWidgets, self.__controlWidget)
            elif self.__widgetType == 'entry':
                self.updateDisplays(self.__displayWidgets)

        # update snapshot (state) file with last-known setting and timing
        self.erl2context['state'].set([(self.controlType,'setting',self.setting),
                                       (self.controlType,'lastChanged',self.settingLastChanged)])

    # placeholder method -- must be overridden in child classes
    def changeHardwareSetting(self):
        pass

    def reportValue(self, period=None):

        # default to control's own logging frequency
        if period is None:
            period = self.__loggingFrequency

        # timing
        currentTime = dt.now(tz=tz.utc)
        oldestTime = currentTime - td(seconds=period)

        # running totals
        runningTotal = 0.
        runningTime = 0.

        # from the previous time through the loop
        lastTime = lastCurr = None

        # loop through all recent values
        for val in self.recentValues:

            # too old
            if val['ts'] < oldestTime:
                lastTime = oldestTime
                lastCurr = val['curr']
                continue

            # too new (probably not possible)
            elif val['ts'] > currentTime:
                break

            # only do the math if value is defined
            if val['prev'] is not None:

                # is this the earliest record?
                if lastTime is None:
                    delta = (val['ts'] - oldestTime).total_seconds()
                    runningTime += delta
                    runningTotal += val['prev'] * delta
                else:
                    delta = (val['ts'] - lastTime).total_seconds()
                    runningTime += delta
                    runningTotal += val['prev'] * delta

            # remember vals from the last time through the loop
            lastTime = val['ts']
            lastCurr = val['curr']

        # current value is added to the mix
        if lastTime is not None and lastCurr is not None:
            delta = (currentTime - lastTime).total_seconds()
            runningTime += delta
            runningTotal += lastCurr * delta

        # final math
        if runningTime > 0.:
            return lastCurr, runningTotal/runningTime
        else:
            return lastCurr, None

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Control',font='Arial 30 bold').grid(row=0,column=0,columnspan=2)
    buttonControl = Erl2Control(controlType='heater',
                                widgetType='button',
                                widgetLoc={'parent':root,'row':2,'column':0},
                                displayLocs=[{'parent':root,'row':1,'column':0}],
                                displayImages=['button-red-30.png','button-green-30.png'],
                                buttonImages=['checkbox-off-25.png','checkbox-off-25.png'],
                                label='Button',
                                )
    entryControl = Erl2Control(controlType='mfc.air',
                               widgetType='entry',
                               widgetLoc={'parent':root,'row':2,'column':1},
                               displayLocs=[{'parent':root,'row':1,'column':1}],
                               label='Entry',
                               )
    buttonControl.setActive()
    entryControl.setActive()
    root.mainloop()

if __name__ == "__main__": main()

