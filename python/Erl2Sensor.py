from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz
from random import random as random
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Log import Erl2Log
from Erl2State import Erl2State
from Erl2Useful import nextIntervalTime

class Erl2Sensor():

    def __init__(self,
                 sensorType='generic',
                 displayLocs=[],
                 statusLocs=[],
                 correctionLoc={},
                 correctionWidth=6,
                 label=None,
                 erl2context={}):

        self.sensorType = sensorType
        self.__displayLocs = displayLocs
        self.__statusLocs = statusLocs
        self.__correctionLoc = correctionLoc
        self.__correctionWidth = correctionWidth
        self.__label = label
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # remember what widgets are active for this sensor
        self.__displayWidgets = []
        self.__statusWidgets = []
        self.__rawWidgets = []
        self.__adjWidgets = []
        self.__offsetEntry = None

        # keep a list of entry widgets
        self.allEntries = []

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # for a sensor, we track current value and last valid update time
        # (be careful to update these values only in the measure() method)
        self.online = True
        self.value = {}
        self.lastValid = self.erl2context['state'].get(self.sensorType,'lastValid',None)

        # read these useful parameters from Erl2Config
        self.__sampleFrequency = self.erl2context['conf'][self.sensorType]['sampleFrequency']
        self.__loggingFrequency = self.erl2context['conf'][self.sensorType]['loggingFrequency']
        self.__systemFrequency = self.erl2context['conf']['system']['loggingFrequency']
        self.__displayParameter = self.erl2context['conf'][self.sensorType]['displayParameter']
        self.__displayDecimals = self.erl2context['conf'][self.sensorType]['displayDecimals']
        self.__offsetParameter = self.erl2context['conf'][self.sensorType]['offsetParameter']
        self.__offsetDefault = self.erl2context['conf'][self.sensorType]['offsetDefault']

        # a record of recent sensor values for running averages
        self.recentValues = []

        # we also keep track of what the active offset parameter is
        # (try to read one back from saved system state)
        self.__offsetFloat = self.erl2context['state'].get(self.sensorType,'offset',self.__offsetDefault)

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # start a data/log file for the sensor
        self.log = Erl2Log(logType='sensor', logName=self.sensorType, erl2context=self.erl2context)

        # loop through the list of needed display widgets for this sensor
        for loc in self.__displayLocs:

            # different frame padding depending on if there's a label or not
            pd = '2 2'
            if self.__label == '|nolabel|': pd = '0 0'

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding=pd, relief='flat', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nesw')

            # add a Label widget to show the current sensor value

            # special case: label is |nolabel|
            if self.__label == '|nolabel|':
                l = ttk.Label(f, text='--', font='Ariel 14', foreground='#1C4587')
                l.grid(row=0, column=0, sticky='nw')

            # if the sensor draws with a label, show both, in slightly smaller font
            elif self.__label is not None:
                l = ttk.Label(f, text='--', font='Arial 19 bold', foreground='#1C4587')
                l.grid(row=0, column=1, padx='2', sticky='e')

                # this is the Label shown beside the text display widget
                ttk.Label(f, text=self.__label, font='Arial 16'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, padx='2 2', sticky='w')

                f.rowconfigure(0,weight=1)
                f.columnconfigure(0,weight=1,minsize=45)
                f.columnconfigure(1,weight=1,minsize=76)

            # if there's no sensor label then draw it larger and centered
            else:
                l = ttk.Label(f, text='--', font='Arial 40 bold', foreground='#1C4587', justify='center'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, sticky='n')

                f.rowconfigure(0,weight=1)
                f.columnconfigure(0,weight=1)

            # keep a list of display widgets for this sensor
            self.__displayWidgets.append(l)

        # loop through the list of needed status widgets for this sensor
        for loc in self.__statusLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='flat', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nw')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text='--', font='Arial 16', foreground='#1C4587')
            l.grid(row=0, column=0, sticky='nw')

            # keep a list of status widgets for this sensor
            self.__statusWidgets.append(l)

        # the offset/raw/correction logic is optional for sensors
        if 'parent' in self.__correctionLoc:

            # create the correction widgets' base frame as a child of its parent
            f = ttk.Frame(self.__correctionLoc['parent'], padding='0 0', relief='flat', borderwidth=0)
            f.grid(row=self.__correctionLoc['row'], column=self.__correctionLoc['column'], padx='2', pady='0', sticky='nw')

            # create the entry field for the correction offset
            self.__offsetEntry = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                                           labelLoc={'parent':f,'row':0,'column':0},
                                           label='Offset',
                                           width=self.__correctionWidth,
                                           displayDecimals=(self.__displayDecimals+2),
                                           #validRange=,
                                           initValue=self.__offsetFloat,
                                           onChange=self.changeOffset,
                                           erl2context=self.erl2context)

            # expose a list of all entry fields so it can be seen by other modules
            self.allEntries.append(self.__offsetEntry)

            # add a Label widget to show the raw sensor value
            l = ttk.Label(f, text='--', font='Arial 16', justify='right')
            l.grid(row=1, column=1, sticky='e')

            ttk.Label(f, text='Raw Value', font='Arial 14'
                #, relief='solid', borderwidth=1
                ).grid(row=1, column=0, padx='2 2', sticky='w')

            self.__rawWidgets.append(l)

            # add a Label widget to show the adjusted sensor value
            l = ttk.Label(f, text='--', font='Arial 16', justify='right')
            l.grid(row=2, column=1, sticky='e')

            ttk.Label(f, text='Adj Value', font='Arial 14'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, padx='2 2', sticky='w')

            self.__adjWidgets.append(l)

            f.rowconfigure(0,weight=1)
            f.rowconfigure(1,weight=1)
            f.columnconfigure(1,weight=1)
            f.columnconfigure(0,weight=0)

        # start up the timing loop to update the display widgets
        # (check first if this object is an Erl2Sensor or a child class)
        if self.__class__.__name__ == 'Erl2Sensor':
            self.readSensor()

    def readSensor(self):

        # make note of previous measurement value
        previousValue = None
        if self.__displayParameter in self.value:
            previousValue = self.value[self.__displayParameter]

        # take a measurement
        currentTime, measurement, online = self.measure()

        # apply the corrective offset
        self.applyOffset(measurement)

        # make note of current measurement value
        currentValue = None
        if self.__displayParameter in self.value:
            currentValue = self.value[self.__displayParameter]

        # keep a record of recent sensor measurement values
        self.recentValues.append({'ts':currentTime, 'prev':previousValue, 'curr':currentValue})

        # filter out recent values that have gotten too old
        tooOld = currentTime - td(seconds=max(self.__loggingFrequency,self.__systemFrequency))
        self.recentValues = [ x for x in self.recentValues if x['ts'] > tooOld ]

        #print (f"{self.__class__.__name__}: Debug: readSensor() receiving [{str(currentTime)}][{str(measurement)}][{str(online)}]")

        # update the display widgets with their current values
        self.updateDisplays(self.__displayWidgets,self.__statusWidgets,self.__rawWidgets,self.__adjWidgets)

        # how long before we should update the display widgets again?
        nextSampleTime = nextIntervalTime(currentTime, self.__sampleFrequency)
        delay = int((nextSampleTime - currentTime.timestamp())*1000)

        # update the display widgets again after waiting an appropriate number of milliseconds
        self.__displayWidgets[0].after(delay, self.readSensor)

        # if we've passed the next file-writing interval time, write it
        if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

            # send the new sensor data to the log (in dictionary form)
            if self.log is not None:

                # only log this measurement if the sensor is online
                if self.online:

                    # add an average value for the reporting period
                    _, measurement['avg.value'] = self.reportValue()

                    # write record to file
                    self.log.writeData(measurement)

        # if the next file-writing interval time is empty or in the past, update it
        if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
            self.__nextFileTime = nextIntervalTime(currentTime, self.__loggingFrequency)

    def updateDisplays(self, displayWidgets, statusWidgets, rawWidgets, adjWidgets):

        #print (f"{self.__class__.__name__}: Debug: updateDisplays() using [{str(self.lastValid)}][{str(self.value)}][{str(self.online)}]")

        # default value and display text
        value = None
        upd = raw = adj = '--'

        # figure out what values to use in update
        if not self.online:
            #if self.sensorType == 'pH':
            #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] is offline")
            pass

        elif len([x for x in self.value.keys() if 'Timestamp' not in x]) == 0:
            #if self.sensorType == 'pH':
            #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] value is empty")
            pass

        elif self.__displayParameter not in self.value:
            raise AttributeError(f"{self.__class__.__name__}: Error: no key named [{self.__displayParameter}] in self.value")

        else:
            # even if the parameter is present, it might not be in float format
            try:
                value = float(self.value[self.__displayParameter])
                upd = f"{round(value,self.__displayDecimals):.{self.__displayDecimals}f}"
                adj = raw = f"{round(value,(self.__displayDecimals+2)):.{(self.__displayDecimals+2)}f}"
                #if self.sensorType == 'pH':
                #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] update is [{upd}]")

                # default to raw=upd, but assuming the raw.value parameter exists, use that
                if 'raw.value' in self.value:
                    raw = f"{float(round(self.value['raw.value'],(self.__displayDecimals+2))):.{(self.__displayDecimals+2)}f}"

            except:
                #if self.sensorType == 'pH':
                #    print (f"{self.__class__.__name__}: Debug updateDisplays() sensor[{self.sensorType}] float exception for [{self.value[self.__displayParameter]}][{self.__displayDecimals}]")
                pass

        # loop through all of this sensor's display widgets
        for w in displayWidgets:

            # update the display
            w.config(text=upd)

        # loop through all of this sensor's offset/raw widgets
        for w in rawWidgets:

            # update the display
            w.config(text=raw)

        # loop through all of this sensor's offset/adjusted widgets
        for w in adjWidgets:

            # update the display
            w.config(text=adj)

        # the status message conveys information about how current the reading is and on/offline status
        if self.lastValid is not None:
            upd = self.lastValid.astimezone(self.__timezone).strftime(self.__dtFormat)
        else:
            upd = 'never'

        if self.online:
            fnt = 'Arial 14'
            fgd = '#1C4587'
        else:
            fnt = 'Arial 14 bold'
            fgd = '#A93226'

        # loop through all placements of this sensor's status widgets
        for w in self.__statusWidgets:

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)

        # save a snapshot of sensor info to the state file
        # n.b. displayDecimals is written (to share w/controller) but never read
        self.erl2context['state'].set([(self.sensorType,'value',value),
                                       (self.sensorType,'lastValid',self.lastValid),
                                       (self.sensorType,'online',self.online),

                                       # this parameter is written (to share w/controller) but never read
                                       (self.sensorType,'displayDecimals',self.__displayDecimals)])

    def getTimestamp(self):

        # record the current timestamp
        currentTime = dt.now(tz=tz.utc)

        # add timestamps to a template measurement dict
        m = {'Timestamp.UTC': currentTime.strftime(self.__dtFormat),
             'Timestamp.Local': currentTime.astimezone(self.__timezone).strftime(self.__dtFormat)}

        return currentTime, m

    # placeholder method -- must be overridden in child classes
    def measure(self):

        # fake measurement
        self.value = {'generic':random()}

        # fake sensor never goes offline
        self.online = True

        # add Timestamps to measurement record
        t, m = self.getTimestamp()

        # produce the final measurement dict with timestamps and values
        self.value = {**m, **self.value}

        # remember timestamp of last valid measurement
        self.lastValid = t

        #print (f"{self.__class__.__name__}: Debug: measure() returning [{str(t)}][{str(self.value)}][{str(self.online)}]")

        # apply the corrective offset
        self.applyOffset(self.value, updateRaw=True)

        # return timestamp, measurement and status
        return t, self.value, self.online

    def applyOffset(self, measurement={}, updateRaw=False):

        # write the current offset into the data
        measurement['offset.value'] = self.__offsetFloat

        # if the offsetParameter matches something in the measurement
        if self.__offsetParameter in measurement:

            # if we've been directed to update the raw.value
            if updateRaw:
                measurement['raw.value'] = measurement[self.__offsetParameter]

            # use the raw.value to update the parameter
            measurement[self.__offsetParameter] = measurement['raw.value'] + measurement['offset.value']

        # otherwise, set the raw.value to nan if we've been directed to update it
        elif updateRaw:
            measurement['raw.value'] = float('nan')

    def changeOffset(self):

        # check if this represents an actual change in value, or just formatting
        if float(self.__offsetEntry.stringVar.get()) != self.__offsetFloat:

            #print (f"{self.__class__.__name__}: Debug: changeOffset({self.sensorType}): change detected: before [{self.__offsetFloat}], after [{float(self.__offsetEntry.stringVar.get())}]")

            # make a note in the log about this change
            if self.log is not None:
                self.log.writeMessage(f"offset value changed from [{self.__offsetFloat}] to [{float(self.__offsetEntry.stringVar.get())}]")

            # update the offset (float) value
            self.__offsetFloat = float(self.__offsetEntry.stringVar.get())

            # re-apply the corrective offset
            self.value['offset.value'] = self.__offsetFloat
            if self.__offsetParameter in self.value and 'raw.value' in self.value:
                self.value[self.__offsetParameter] = self.value['raw.value'] + self.value['offset.value']
                #print (f"{self.__class__.__name__}: Debug: changeOffset({self.sensorType}|{self.__offsetParameter}) new value is [{self.value[self.__offsetParameter]}]")

            # redraw the app's displays immediately
            self.updateDisplays(self.__displayWidgets,self.__statusWidgets,self.__rawWidgets, self.__adjWidgets)

            # notify application that its state has changed
            self.erl2context['state'].set([(self.sensorType,'offset',self.__offsetFloat)])

    def reportValue(self, period=None):

        # default to sensor's own logging frequency
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
    ttk.Label(root,text='Erl2Sensor',font='Arial 30 bold').grid(row=0,column=0)

    statusFrame = ttk.Frame(root)
    statusFrame.grid(row=3,column=0)
    ttk.Label(statusFrame,text='Sensor last read:',font='Arial 14 bold',justify='right').grid(row=0,column=0,sticky='nes')

    sensor = Erl2Sensor(displayLocs=[{'parent':root,'row':1,'column':0}],
                        statusLocs=[{'parent':statusFrame,'row':0,'column':1}],
                        correctionLoc={'parent':root,'row':2,'column':0},
                        correctionWidth=8)
    root.mainloop()

if __name__ == "__main__": main()

