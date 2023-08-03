#! /usr/bin/python3

from datetime import datetime as dt
from datetime import timezone as tz
from megaind import get4_20In,set0_10Out
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Input4_20 import Erl2Input4_20
from Erl2Log import Erl2Log

# MFC = Mass Flow Controllers (gas rates for Air, CO2, N2)

class Erl2Mfc():

    def __init__(self,
                 controlType='generic',
                 settingDisplayLocs=[],
                 entryLoc={},
                 label=None,
                 width=5,
                 erl2context={}):

        self.controlType = controlType
        self.__settingDisplayLocs = settingDisplayLocs
        self.__entryLoc = entryLoc
        self.__label = label
        self.__width = width
        self.erl2context = erl2context

        # if no label supplied, try to deduce from MFC control type
        if self.__label is None:
            if self.controlType == 'mfc.air':
                self.__label = 'Air'
            elif self.controlType == 'mfc.co2':
                self.__label = u'CO\u2082'
            elif self.controlType == 'mfc.n2':
                self.__label = u'N\u2082'
            else:
                self.__label = self.controlType[4:]

        # placeholder for this MFC control to be told what subsystem it's part of
        self.subSystem = None

        # remember what widgets are active for this MFC control
        self.__settingDisplayWidgets = []
        self.__entryWidget = None

        # and whether the entry fields are allowed to be active or not
        self.enabled = 0

        # for an MFC control, we track flow setting and history
        self.flowSetting = 0.
        self.settingLastChanged = None
        self.flowActual = 0
        self.offSeconds = []
        self.onSeconds = []
        self.allSeconds = []
        self.allValues = []
        self.numChanges = 0

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # read these useful parameters from Erl2Config
        self.__stackLevel = self.erl2context['conf'][self.controlType]['stackLevel']
        #self.__inputChannel = self.erl2context['conf'][self.controlType]['inputChannel']
        self.__outputChannel = self.erl2context['conf'][self.controlType]['outputChannel']
        self.__flowRateRange = self.erl2context['conf'][self.controlType]['flowRateRange']
        self.__displayDecimals = self.erl2context['conf'][self.controlType]['displayDecimals']
        #self.__sampleFrequency = self.erl2context['conf'][self.controlType]['sampleFrequency']
        self.__loggingFrequency = self.erl2context['conf'][self.controlType]['loggingFrequency']

        # start a data/log file for the control
        if not self.erl2context['conf']['system']['disableFileLogging']:
            self.log = Erl2Log(logType='control', logName=self.controlType, erl2context=self.erl2context)
        else:
            self.log = None

        # loop through the list of needed setting display widgets for this control
        for loc in self.__settingDisplayLocs:

            # create the setting display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nwse')

            # add a Label widget to show the current MFC flow rate
            l = ttk.Label(f, text=f"{float(round(self.flowSetting,self.__displayDecimals)):.{self.__displayDecimals}f}", font='Arial 8', justify='right'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2', pady='0', sticky='e')

            # this is the Label shown beside the text display widget
            ttk.Label(f, text='Setting', font='Arial 8'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, padx='2', pady='0', sticky='w')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1,minsize=45)
            f.columnconfigure(1,weight=1,minsize=76)

            # keep a list of display widgets for this control
            self.__settingDisplayWidgets.append(l)

        # create the entry widget's base frame as a child of its parent
        f = ttk.Frame(self.__entryLoc['parent'], padding='2 2', relief='solid', borderwidth=0)
        f.grid(row=self.__entryLoc['row'], column=self.__entryLoc['column'], padx='2', pady='0', sticky='nwse')

        #print (f"{self.__class__.__name__}: Debug: {self.controlType} valid range is {str(self.__flowRateRange)}")

        # add an entry widget to change the current setting of the control
        e = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                      labelLoc={'parent':f,'row':0,'column':0},
                      label=self.__label,
                      width=self.__width,
                      labelFont='Arial 16',
                      displayDecimals=self.__displayDecimals,
                      validRange=self.__flowRateRange,
                      initValue=self.flowSetting,
                      onChange=self.changeFlow,
                      erl2context=self.erl2context)

        f.rowconfigure(0,weight=1)
        f.columnconfigure(0,weight=0)
        f.columnconfigure(1,weight=1)

        # keep track of the entry widget for this control
        self.__entryWidget = e

        # now set each control's enabled state individually
        self.setActive(self.enabled)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Mfc or a child class)
        if self.__class__.__name__ == 'Erl2Mfc':
            self.updateLog()

    def updateLog(self):

        # remember the timestamp at the exact moment of logging
        currentTime = dt.now(tz=tz.utc)

        #print (f"{self.__class__.__name__}: Debug: updateLog() called [{str(currentTime)}]")

        # did we just start up?
        if self.settingLastChanged is None:
            timing = 0
            self.settingLastChanged = currentTime

        # otherwise calculate how long has the system been in its current state
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
        if self.flowSetting > 0.:
            onTime += timing
        else:
            offTime += timing

        # figure out what to report as the average flow setting
        if sum(self.allSeconds) + timing > 0.:
            avgSetting = (sum(self.allValues) + timing * self.flowSetting) / (sum(self.allSeconds) + timing)
        else:
            avgSetting = float('nan')

        self.allSeconds = []
        self.allValues = []

        # is file logging enabled?
        if not self.erl2context['conf']['system']['disableFileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

                # create a dict of values we want to log
                m = {'Timestamp.UTC': currentTime.strftime(self.erl2context['conf']['system']['dtFormat']),
                     'Timestamp.Local': currentTime.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']),
                     'Current Flow Setting': self.flowSetting,
                     'Average Flow Setting': avgSetting,
                     'Off (seconds)': offTime,
                     'On (seconds)': onTime,
                     'Setting Changes (count)':changes,
                     'Setting Last Changed (Local)': self.settingLastChanged.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat'])}

                # send the new sensor data to the log (in dictionary form)
                if self.log is not None:
                    self.log.writeData(m)

        # if the next file-writing interval time is empty or in the past, update it
        if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
            self.__nextFileTime = (
              (
                int(
                  currentTime.timestamp()   # timestamp in seconds
                  / self.__loggingFrequency # convert to number of intervals of length loggingFrequency
                )                           # truncate to beginning of previous interval (past)
              + 1)                          # advance by one time interval (future)
              * self.__loggingFrequency     # convert back to seconds/timestamp
            )

        # when should this method be called next? (milliseconds)
        delay = int((self.__nextFileTime - currentTime.timestamp())*1000)

        # update the display widget(s) again after waiting an appropriate number of milliseconds
        self.__settingDisplayWidgets[0].after(delay, self.updateLog)

        #print (f"{self.__class__.__name__}: Debug: updateLog() to be called again after [{float(delay)/1000.}] seconds")

    def setActive(self, enabled=1):

        # remember if controls are enabled or not
        self.enabled = enabled

        # loop through all placements of this control's entry widgets
        if self.__entryWidget is not None:

            # update the control's enabled state
            if self.enabled:
                self.__entryWidget.setActive(1)
            else:
                self.__entryWidget.setActive(0)

    def updateDisplays(self, settingDisplayWidgets):

        # format the values to be displayed
        setting = f"{float(round(self.flowSetting,self.__displayDecimals)):.{self.__displayDecimals}f}"

        # loop through all placements of this control's setting display widgets
        for w in settingDisplayWidgets:

            # update the setting display
            w.config(text=setting)

    def changeFlow(self, event=None):

        # pull new flow rate from entry field and apply it
        self.setControl(float(self.__entryWidget.stringVar.get()))

        # if this control has a subsystem, notify it of this change
        if self.subSystem is not None:

            # the subsystem will only log this change if it's made in Manual mode
            self.subSystem.controlsLog(f"{self.controlType} setting was manually changed to {self.flowSetting}")

    def setControl(self, newSetting=0.):

        # do nothing if no change is required
        if self.flowSetting == float(newSetting):
            return

        # it's an error to try to set an MFC to a value outside its range
        assert self.__flowRateRange[0] <= float(newSetting) <= self.__flowRateRange[1]

        # tally up how many times the setting is changing
        self.numChanges += 1

        # make note of previous setting, and remember what the current setting is
        previousFlowSetting = self.flowSetting
        self.flowSetting = float(newSetting)

        # apply the new setting to the control's hardware
        self.changeHardwareSetting()

        # remember the time that the setting was changed
        currentTime = dt.now(tz=tz.utc)

        # default the last-changed time to now if it hasn't already been set
        if self.settingLastChanged is None:
            self.settingLastChanged = currentTime

        # calculate how long the system had been in its prior setting
        # (but don't count earlier than the start of the current interval)
        fromTime = max(self.settingLastChanged.timestamp(),
                       self.__nextFileTime - self.__loggingFrequency)
        timing = currentTime.timestamp() - fromTime

        # add this timing to the tally of cumulative off/on time
        if previousFlowSetting > 0.:
            self.onSeconds.append(timing)
        else:
            self.offSeconds.append(timing)

        # additionally, tally up all times and weighted values
        self.allSeconds.append(timing)
        self.allValues.append(timing*previousFlowSetting)

        # save the new last-changed time
        self.settingLastChanged = currentTime

        # make a note in the log about this change
        if self.log is not None:
            self.log.writeMessage(f"flow setting changed from [{self.flowSetting}] to [{float(self.__entryWidget.stringVar.get())}]")

        # redraw the app's displays immediately
        self.updateDisplays(self.__settingDisplayWidgets)

    def changeHardwareSetting(self):

        # calculate the Vdc that corresponds to the current setting
        volts = (self.flowSetting - self.__flowRateRange[0]) / (self.__flowRateRange[1] - self.__flowRateRange[0]) * 5.

        # don't exceed the range of 0 - 5 V
        if volts > 5.:
            volts = 5.
        elif volts < 0.:
            volts = 0.

        #print (f"{self.__class__.__name__}: Debug: changeHardwareSetting(): setting is [{self.flowSetting}], volts is [{volts}]")

        # apply this voltage to the output channel
        set0_10Out(self.__stackLevel,self.__outputChannel,volts)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Mfc',font='Arial 30 bold').grid(row=0,column=0,columnspan=3)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=4,column=0,columnspan=3)
    ttk.Label(statusFrame,text='Air MFC last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nse')
    ttk.Label(statusFrame,text='CO2 MFC last read:',font='Arial 14 bold',justify='right').grid(row=1,column=0,sticky='nse')
    ttk.Label(statusFrame,text='N2 MFC last read:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nse')

    sensorMfcAir = Erl2Input4_20(sensorType='mfc.air',
                                 displayLocs=[{'parent':root,'row':1,'column':0}],
                                 statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                                 label='Air'
                                 )
    sensorMfcCO2 = Erl2Input4_20(sensorType='mfc.co2',
                                 displayLocs=[{'parent':root,'row':1,'column':1}],
                                 statusLocs=[{'parent':statusFrame,'row':1,'column':1}],
                                 label=u'CO\u2082'
                                 )
    sensorMfcN2  = Erl2Input4_20(sensorType='mfc.n2',
                                 displayLocs=[{'parent':root,'row':1,'column':2}],
                                 statusLocs=[{'parent':statusFrame,'row':2,'column':1}],
                                 label=u'N\u2082'
                                 )

    controlMfcAir = Erl2Mfc(controlType='mfc.air',
                            settingDisplayLocs=[{'parent':root,'row':2,'column':0}],
                            entryLoc={'parent':root,'row':3,'column':0},
                            )
    controlMfcCO2 = Erl2Mfc(controlType='mfc.co2',
                            settingDisplayLocs=[{'parent':root,'row':2,'column':1}],
                            entryLoc={'parent':root,'row':3,'column':1},
                            )
    controlMfcN2 =  Erl2Mfc(controlType='mfc.n2',
                            settingDisplayLocs=[{'parent':root,'row':2,'column':2}],
                            entryLoc={'parent':root,'row':3,'column':2},
                            )
    controlMfcAir.setActive()
    controlMfcCO2.setActive()
    controlMfcN2.setActive()
    root.mainloop()

if __name__ == "__main__": main()

