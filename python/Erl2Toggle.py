#! /usr/bin/python3

from datetime import datetime as dt
from tkinter import *
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log

class Erl2Toggle():

    def __init__(self,
                 type='generic',
                 displayLocs=[],
                 buttonLocs=[],
                 displayImages=[],
                 buttonImages=[],
                 label='Generic',
                 erl2conf=None,
                 img=None):

        self.__controlType = type
        self.__displayLocs = displayLocs
        self.__buttonLocs = buttonLocs
        self.displayImages = displayImages
        self.buttonImages = buttonImages
        self.__label = label
        self.__erl2conf = erl2conf
        self.img = img

        # remember what widgets are active for this control
        self.__displayWidgets = []
        self.__buttonWidgets = []

        # and whether the buttons are allowed to be active or not
        self.enabled = True

        # for a toggle control, we track on/off state and history
        self.state = 0
        self.stateLastChanged = None
        self.offSeconds = []
        self.onSeconds = []

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # if necessary, create an object to hold/remember image objects
        if self.img is None:
            self.img = Erl2Image(erl2conf=self.__erl2conf)

        # load the associated images; just use the image name as the key
        for i in self.displayImages + self.buttonImages:
            self.img.addImage(i,i)

        # start a data/log file for the control
        if self.__erl2conf['system']['fileLogging']:
            self.dataLog = Erl2Log(logType='control', logName=self.__controlType, erl2conf=self.__erl2conf)
        else:
            self.dataLog = None

        # loop through the list of needed display widgets for this control
        for loc in self.__displayLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='2', sticky='nwse')

            # add a Label widget to show the current control value
            l = ttk.Label(f, image=self.img[self.displayImages[0]])
            l.grid(row=0, column=1, padx='2 2', sticky='e')

            # this is the (text) Label shown beside the (image) display widget
            ttk.Label(f, text=self.__label, font='Arial 16'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, padx='2 2', sticky='w')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)
            f.columnconfigure(1,weight=0)

            # keep a list of display widgets for this control
            self.__displayWidgets.append(l)

        # loop through the list of needed button widgets for this control
        for loc in self.__buttonLocs:

            # create the button widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nwse')

            # add a Button widget to change the state of the control
            b = Button(f, image=self.img[self.buttonImages[0]], height=40, width=40, bd=0, highlightthickness=0, activebackground='#DBDBDB', command=self.changeState)
            b.grid(row=0, column=1, padx='2 2', sticky='e')

            # this is the (text) Label shown beside the (image) button widget
            ttk.Label(f, text=self.__label, font='Arial 16'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, padx='2 2', sticky='w')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)
            f.columnconfigure(1,weight=0)

            # keep a list of button widgets for this control
            self.__buttonWidgets.append(b)

        # now set each control's enabled state individually
        self.setActive(self.enabled)

    def updateLog(self):

        # remember the timestamp at the exact moment of logging
        currentTime = dt.utcnow()

        #print (f"{self.__class__.__name__}: Debug: updateLog() called [{str(currentTime)}]")

        # did we just start up?
        if self.stateLastChanged is None:
            timing = 0
            self.stateLastChanged = currentTime

        # otheewise calculate how long has the system been in its current state
        # (limited to the current logging interval)
        else:
            timing = currentTime.timestamp() - self.stateLastChanged.timestamp()
            timing = min(timing, self.__erl2conf[self.__controlType]['loggingFrequency'])

        # add up on+off times, then reset them
        onTime = sum(self.onSeconds)
        self.onSeconds = []
        offTime = sum(self.offSeconds)
        self.offSeconds = []

        # include current timing as appropriate
        if self.state:
            onTime += timing
        else:
            offTime += timing

        # is file logging enabled?
        if self.__erl2conf['system']['fileLogging']:

            # if we've passed the next file-writing interval time, write it
            if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

                # create a dict of values we want to log
                m = {'Timestamp': currentTime.strftime(self.__erl2conf['system']['dtFormat']), 
                     'Current State': self.state,
                     'Off (seconds)': offTime,
                     'On (seconds)': onTime,
                     'Last State Change': self.stateLastChanged}

                # send the new sensor data to the log (in dictionary form)
                if self.dataLog is not None:
                    self.dataLog.writeData(m)

        # if the next file-writing interval time is empty or in the past, update it
        if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
            self.__nextFileTime = (
              (
                int(
                  currentTime.timestamp()                                  # timestamp in seconds
                  / self.__erl2conf[self.__controlType]['loggingFrequency'] # convert to number of intervals of length loggingFrequency
                )                                                          # truncate to beginning of previous interval (past)
              + 1)                                                         # advance by one time interval (future)
              * self.__erl2conf[self.__controlType]['loggingFrequency']     # convert back to seconds/timestamp
            )

        # when should this method be called next? (milliseconds)
        delay = int((self.__nextFileTime - currentTime.timestamp())*1000)

        # update the display widget(s) again after waiting an appropriate number of milliseconds
        self.__displayWidgets[0].after(delay, self.updateLog)

        #print (f"{self.__class__.__name__}: Debug: updateLog() to be called again after [{float(delay)/1000.}] seconds")

    def setActive(self, enabled=True):

        # loop through all placements of this control's button widgets
        wcount = 0
        for w in self.__buttonWidgets:

            # remember if controls are enabled or not
            self.enabled = enabled

            # update the control's enabled state
            if self.enabled:
                #w.config(command=self.changeState)
                w.config(state='normal')
            else:
                #w.config(command=False)
                w.config(state='disabled')

            # increment counter
            wcount += 1

    def updateDisplays(self, displayWidgets, buttonWidgets):

        # loop through all placements of this control's display widgets
        for w in displayWidgets:

            # update the display
            w.config(image=self.img[self.displayImages[self.state]])

        # loop through all placements of this control's button widgets
        for w in buttonWidgets:

            # update the button
            w.config(image=self.img[self.buttonImages[self.state]])

    def changeState(self):

        # toggle state
        self.setState(1 - self.state)

    def setState(self, newState=0):

        # do nothing if no change is required
        if self.state == int(newState):
            return

        # remember what the current state is
        self.state = int(newState)

        # update the control's buttons to show correct on/off image
        self.updateDisplays(self.__displayWidgets, self.__buttonWidgets)

        # apply the new state to the control's hardware
        self.changeHardwareState()

        # remember the time that the state was changed
        currentTime = dt.utcnow()

        # calculate how long the system had been in its prior state
        # (but don't count earlier than the start of the current interval)
        fromTime = max(self.stateLastChanged.timestamp(),
                       self.__nextFileTime - self.__erl2conf[self.__controlType]['loggingFrequency'])
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

    # placeholder method -- must be overwritten in child classes
    def changeHardwareState(self):

        raise SystemError(f"{self.__class__.__name__}: Error: Erl2Toggle.changeHardwareState() method must be overridden in child classes")

def main():

    root = Tk()
    toggle = Erl2Toggle(root)
    root.mainloop()

if __name__ == "__main__": main()

