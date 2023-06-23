#! /usr/bin/python3

from datetime import datetime as dt
from tkinter import *
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2Toggle():

    def __init__(self, parent, clones=[], disableOn=[], type='generic', row=0, column=0, label='Generic', offImage='button-grey-30.png', onImage='button-green-30.png', erl2conf=None, img=None):
        self.__parent = parent
        self.__clones = clones
        self.__disableOn = disableOn
        self.__controlType = type
        self.__row = row
        self.__column = column
        self.__label = label
        self.offImage = offImage
        self.onImage = onImage
        self.__erl2conf = erl2conf
        self.img = img

        # remember what widgets are active for this control
        self.__controlWidgets = []

        # and whether the control is allowed to be active or not
        self.enabled = True

        # for a toggle control, we track on/off state and history
        self.state = 0
        self.stateLastChanged = None
        self.offSeconds = []
        self.onSeconds = []

        # keep track of when the file-writing intervals are
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
        self.img.addImage(self.offImage,self.offImage)
        self.img.addImage(self.onImage,self.onImage)

        # start a data/log file for the control
        if self.__erl2conf['system']['fileLogging']:
            self.dataLog = Erl2Log(logType='control', logName=self.__controlType, erl2conf=self.__erl2conf)
        else:
            self.dataLog = None

        # loop through the control's primary parent and all of its clones
        for par in [self.__parent] + self.__clones:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(par, padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=self.__row, column=self.__column, padx='2', pady='2', sticky='nwse')

            ttk.Label(f, text=self.__label, font='Arial 16'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, padx='2 2', sticky='w')
            b = Button(f, image=self.img[self.offImage], height=40, width=40, bd=0, highlightthickness=0, activebackground='#DBDBDB', command=self.changeState)
            b.grid(row=0, column=1, padx='2 2', sticky='e')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)
            f.columnconfigure(1,weight=0)

            # keep a list of widgets for this control
            self.__controlWidgets.append(b)

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
                  currentTime.timestamp()                                   # timestamp in seconds
                  / self.__erl2conf[self.__controlType]['loggingFrequency'] # convert to number of intervals of length loggingFrequency
                )                                                           # truncate to beginning of previous interval (past)
              + 1)                                                          # advance by one time interval (future)
              * self.__erl2conf[self.__controlType]['loggingFrequency']     # convert back to seconds/timestamp
            )

        # when should this method be called next? (milliseconds)
        delay = int((self.__nextFileTime - currentTime.timestamp())*1000)

        # update the display widget(s) again after waiting an appropriate number of milliseconds
        self.__controlWidgets[0].after(delay, self.updateLog)

        #print (f"{self.__class__.__name__}: Debug: updateLog() to be called again after [{float(delay)/1000.}] seconds")

    def setActive(self, enabled=True):

        #print (f"{self.__class__.__name__}: Debug: setActive([{enabled}]) called")
        
        # loop through all placements of this control's widgets
        wcount = 0
        for w in self.__controlWidgets:

            # remember if controls are enabled or not
            self.enabled = enabled

            # figure out if each individual widget should be enabled
            disabledAlways = (wcount < len(self.__disableOn) and self.__disableOn[wcount])
            disableThis = disabledAlways or not self.enabled

            #print (f"{self.__class__.__name__}: Debug: setActive() wcount [{wcount}] disableThis set to [{disableThis}]")

            # update the control's enabled state
            if disableThis:
                w.config(command=False)
            else:
                w.config(command=self.changeState)

            # increment counter
            wcount += 1

    def updateDisplays(self, widgets):

        # what image should be used for the new setting?
        if self.state: i = self.onImage
        else: i = self.offImage

        # loop through all placements of this control's widgets
        for w in widgets:

            # update the display
            w.config(image=self.img[i])
            w.config(bd=0)

    def changeState(self):
        # toggle state
        self.state = 1 - self.state

        # update the control's buttons to show correct on/off image
        self.updateDisplays(self.__controlWidgets)

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

    def changeHardwareState(self):

        # placeholder method -- must be overwritten in child classes
        pass

def main():

    root = Tk()
    toggle = Erl2Toggle(root)
    root.mainloop()

if __name__ == "__main__": main()

