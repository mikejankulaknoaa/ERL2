#! /usr/bin/python3

from datetime import datetime as dt
from datetime import timezone as tz
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log

class Erl2Toggle():

    def __init__(self,
                 controlType='generic',
                 displayLocs=[],
                 buttonLoc={},
                 displayImages=['button-grey-30.png','button-green-30.png'],
                 buttonImages=['radio-off-30.png','radio-on-30.png'],
                 label='Generic',
                 erl2context={}):

        self.controlType = controlType
        self.__displayLocs = displayLocs
        self.__buttonLoc = buttonLoc
        self.displayImages = displayImages
        self.buttonImages = buttonImages
        self.__label = label
        self.erl2context = erl2context

        # placeholder for this control to be told what subsystem it's part of
        self.subSystem = None

        # remember what widgets are active for this control
        self.__displayWidgets = []
        self.__buttonWidget = None
        self.__labelWidget = None

        # and whether the buttons are allowed to be active or not
        self.enabled = 0

        # for a toggle control, we track on/off state and history
        self.state = 0
        self.stateLastChanged = None
        self.offSeconds = []
        self.onSeconds = []
        self.numChanges = 0

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # read this useful parameter from Erl2Config
        self.__loggingFrequency = self.erl2context['conf'][self.controlType]['loggingFrequency']

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load the associated images; just use the image name as the key
        for i in self.displayImages + self.buttonImages:
            self.erl2context['img'].addImage(i,i)

        # start a data/log file for the control
        if not self.erl2context['conf']['system']['disableFileLogging']:
            self.log = Erl2Log(logType='control', logName=self.controlType, erl2context=self.erl2context)
        else:
            self.log = None

        # loop through the list of needed display widgets for this control
        for loc in self.__displayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='2', sticky='nwse')

            # add a Label widget to show the current control value
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

            # keep a list of display widgets for this control
            self.__displayWidgets.append(l)

        # create the button widget's base frame as a child of its parent
        f = ttk.Frame(self.__buttonLoc['parent'], padding='2 2', relief='solid', borderwidth=0)
        f.grid(row=self.__buttonLoc['row'], column=self.__buttonLoc['column'], padx='2', pady='0', sticky='nwse')

        # add a button widget to change the state of the control
        b = tk.Button(f,
                      image=self.erl2context['img'][self.buttonImages[0]],
                      height=40,
                      width=40,
                      bd=0,
                      highlightthickness=0,
                      activebackground='#DBDBDB',
                      command=self.changeState)
        b.grid(row=0, column=0, padx='2 2', sticky='w')

        # this is the (text) Label shown beside the (image) button widget
        l = ttk.Label(f, text=self.__label, font='Arial 14'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.changeState)

        f.rowconfigure(0,weight=1)
        f.columnconfigure(0,weight=0)
        f.columnconfigure(1,weight=1)

        # keep track of button + label widgets for this control
        self.__buttonWidget = b
        self.__labelWidget = l

        # now set each control's enabled state individually
        self.setActive(self.enabled)

        # start up the timing loop to log control metrics to a log file
        # (check first if this object is an Erl2Toggle or a child class)
        if self.__class__.__name__ == 'Erl2Toggle':
            self.updateLog()

    def updateLog(self):

        # remember the timestamp at the exact moment of logging
        currentTime = dt.now(tz=tz.utc)

        #print (f"{self.__class__.__name__}: Debug: updateLog() called [{str(currentTime)}]")

        # did we just start up?
        if self.stateLastChanged is None:
            timing = 0
            self.stateLastChanged = currentTime

        # otherwise calculate how long has the system been in its current state
        # (limited to the current logging interval)
        else:
            timing = currentTime.timestamp() - self.stateLastChanged.timestamp()
            timing = min(timing, self.__loggingFrequency)

        # add up on+off times, then reset them
        onTime = sum(self.onSeconds)
        self.onSeconds = []
        offTime = sum(self.offSeconds)
        self.offSeconds = []

        # remember the number of state changes, then reset those too
        changes = self.numChanges
        self.numChanges = 0

        # include current timing as appropriate
        if self.state:
            onTime += timing
        else:
            offTime += timing

        # is file logging enabled?
        if not self.erl2context['conf']['system']['disableFileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

                # create a dict of values we want to log
                m = {'Timestamp.UTC': currentTime.strftime(self.erl2context['conf']['system']['dtFormat']),
                     'Timestamp.Local': currentTime.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']),
                     'Current State': self.state,
                     'Off (seconds)': offTime,
                     'On (seconds)': onTime,
                     'State Changes (count)':changes,
                     'State Last Changed (Local)': self.stateLastChanged.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat'])}

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
        self.__displayWidgets[0].after(delay, self.updateLog)

        #print (f"{self.__class__.__name__}: Debug: updateLog() to be called again after [{float(delay)/1000.}] seconds")

    def setActive(self, enabled=1):

        # remember if controls are enabled or not
        self.enabled = enabled

        # loop through all placements of this control's button widgets
        if self.__buttonWidget is not None:

            # update the control's enabled state
            if self.enabled:
                self.__buttonWidget.config(state='normal')
            else:
                self.__buttonWidget.config(state='disabled')

        # loop through all placements of this control's button labels
        if self.__labelWidget is not None:

            # update the label's event binding
            if self.enabled:
                self.__labelWidget.bind('<Button-1>', self.changeState)
            else:
                self.__labelWidget.unbind('<Button-1>')

    def updateDisplays(self, displayWidgets, buttonWidget):

        # loop through all placements of this control's display widgets
        for w in displayWidgets:

            # update the display
            w.config(image=self.erl2context['img'][self.displayImages[self.state]])

        # loop through all placements of this control's button widgets
        if buttonWidget is not None:

            # for a button to diplay the 'on' image, two things are required:
            # the control must be in the on state, and the button must be enabled
            imageInd = self.enabled * self.state

            # update the button
            buttonWidget.config(image=self.erl2context['img'][self.buttonImages[imageInd]])

    def changeState(self, event=None):

        # toggle state
        self.setControl(1 - self.state)

        # if this control has a subsystem, notify it of this change
        if self.subSystem is not None:

            # the subsystem will only log this change if it's made in Manual mode
            self.subSystem.controlsLog(f"{self.controlType} state was manually changed to {self.state}")

    def setControl(self, newState=0):

        # do nothing if no change is required
        if self.state == int(newState):
            return

        # tally up how many times the state is changing
        self.numChanges += 1

        # remember what the current state is
        self.state = int(newState)

        # update the control's buttons to show correct on/off image
        self.updateDisplays(self.__displayWidgets, self.__buttonWidget)

        # apply the new state to the control's hardware
        self.changeHardwareState()

        # remember the time that the state was changed
        currentTime = dt.now(tz=tz.utc)

        # default the last-changed time to now if it hasn't already been set
        if self.stateLastChanged is None:
            self.stateLastChanged = currentTime

        # calculate how long the system had been in its prior state
        # (but don't count earlier than the start of the current interval)
        fromTime = max(self.stateLastChanged.timestamp(),
                       self.__nextFileTime - self.__loggingFrequency)
        timing = currentTime.timestamp() - fromTime

        # add this timing to the tally of cumulative off/on time
        if self.state:
            # just turned ON... tally OFF time
            self.offSeconds.append(timing)
        else:
            # just turned OFF... tally ON time
            self.onSeconds.append(timing)

        # save the new last-changed time
        self.stateLastChanged = currentTime

        # make a note in the log about this change
        if self.log is not None:
            self.log.writeMessage(f"state changed to [{self.state}]")

    # placeholder method -- must be overwritten in child classes
    def changeHardwareState(self):
        pass

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Toggle').grid(row=0,column=0)
    toggle = Erl2Toggle(displayLocs=[{'parent':root,'row':1,'column':0}],
                        buttonLoc={'parent':root,'row':2,'column':0})
    toggle.setActive()
    root.mainloop()

if __name__ == "__main__": main()

