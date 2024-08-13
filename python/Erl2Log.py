# on windows load fsync instead of sync
_syncLoaded = False
_fsyncLoaded = False
try:
    from os import sync
    _syncLoaded = True
except:
    try:
        from os import fsync
        _fsyncLoaded = True
    except:
        pass

from csv import DictReader,DictWriter,writer
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz
from os import makedirs,path
from re import sub as re_sub
from sys import version_info
from Erl2Config import Erl2Config
from Erl2State import Erl2State
from Erl2Useful import SUBSYSTEMS,moveFile

class Erl2Log():

    # remember what kinds of logs have already been instantiated
    logTypes = {}

    def __init__(self, logType='generic', logName='generic', erl2context={}):
        self.__logType = logType
        self.__logName = logName
        self.__logHeader = re_sub('_[0-9]{3}$','',logName)
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']
        self.__memoryRetention = self.erl2context['conf']['system']['memoryRetention']
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__systemFrequency = self.erl2context['conf']['system']['loggingFrequency']

        # trigger an error if the sync method (or fsync on windows) failed to load
        assert(_syncLoaded or (erl2context['conf']['system']['platform'] == 'win32' and _fsyncLoaded))

        # keep a global record of what kind of log types we've been asked to create
        Erl2Log.logTypes[self.__logType] = True

        # we'll keep a certain number of measurements resident in-memory for plotting
        self.history = []
        self.earliestTS = None
        self.latestTS = None

        # this module requires Python 3.7 or higher
        # (the release when dictionaries are guaranteed to be ordered)
        try:
            assert version_info > (3,7)
        except:
            print (f"{self.__class__.__name__}: Error: Python 3.7 or higher is required for this system")
            raise

        # determine location of main logging directory
        self.__logDir = self.erl2context['conf']['system']['logDir'] + '/' + self.__logType
        self.__summaryDir = self.erl2context['conf']['system']['logDir'] + '/summary'
        try:
            # if the startup instance isn't defined, reroute to a debug directory
            if 'startup' not in self.erl2context:
                self.__logDir = self.erl2context['conf']['system']['logDir'] + '/zDebug/' + self.__logType
                self.__logDir = self.erl2context['conf']['system']['logDir'] + '/zDebug/summary'

        except Exception as e:
            print (f"{self.__class__.__name__}: Error: Could not determine location of main logging directory: {e}")
            raise

        # internal attributes
        self.__logMessages = self.__logDir + '/' + self.__logName + '.txt'
        self.__logData = self.__logDir + '/' + self.__logName + '.csv'

        # initial directories (create if missing, including parents)
        makedirs(self.__logDir, exist_ok=True)

        # # initial messaging
        # self.writeMessage(f'{self.__class__.__name__}[{self.__logType}][{self.__logName}]: log initialized')

        # are there any data records to be read in?
        if path.isfile(self.__logData) and path.getsize(self.__logData) > 0:

            # try to read in the old data to memory
            with open(self.__logData, 'r', newline='') as f:

                # use "generator" syntax to strip out NULLs and drop blank lines
                lines = (x.replace('\x00','') for x in f if x.replace('\x00','') != '')

                # pass the generator along to DictReader, and convert to list
                r = DictReader(lines, dialect='unix')
                self.history = list(r)

            # make a note of the earliest and latest timestamps in the history file, before trimming what's kept in memory
            if len(self.history) > 0:
                ts = self.strToUtcDatetime(self.history[0]['Timestamp.UTC'])
                if self.earliestTS is None or ts < self.earliestTS:
                    self.earliestTS = ts
                    #print (f"{__class__.__name__}: Debug: __init__({self.__logType},{self.__logName}): self.earliestTS [{self.earliestTS}]")

                ts = self.strToUtcDatetime(self.history[len(self.history)-1]['Timestamp.UTC'])
                if self.latestTS is None or ts < self.latestTS:
                    self.latestTS = ts
                    #print (f"{__class__.__name__}: Debug: __init__({self.__logType},{self.__logName}): self.latestTS [{self.latestTS}]")

            # calculate the oldest timestamp that should be kept in memory
            oldestTS = dt.now(tz=tz.utc) - td(seconds=self.__memoryRetention)

            # delete any historical data older than the retention timeframe
            self.history = [ x for x in self.history if self.strToUtcDatetime(x['Timestamp.UTC']) > oldestTS ]

        # # make a note if we've reloaded anything from memory
        # if len(self.history) > 0:
        #     self.writeMessage(f'{self.__class__.__name__}[{self.__logType}][{self.__logName}]: loaded [{len(self.history)}] record(s) from existing data files')

    def writeData(self, data):

        # see if earliest or latest timestamps need to be updated
        if 'Timestamp.UTC' in data:
            ts = self.strToUtcDatetime(data['Timestamp.UTC'])
            if self.earliestTS is None or ts < self.earliestTS:
                self.earliestTS = ts
                #print (f"{__class__.__name__}: Debug: writeData({self.__logType},{self.__logName}): self.earliestTS [{self.earliestTS}]")
            if self.latestTS is None or ts > self.latestTS:
                self.latestTS = ts
                #print (f"{__class__.__name__}: Debug: writeData({self.__logType},{self.__logName}): self.latestTS [{self.latestTS}]")

        # first, add the new data point to in-memory history
        self.history.append(data)

        # calculate the oldest timestamp that should be kept in memory
        oldestTS = dt.now(tz=tz.utc) - td(seconds=self.__memoryRetention)

        # delete any historical data older than the retention timeframe
        self.history = [ x for x in self.history if self.strToUtcDatetime(x['Timestamp.UTC']) > oldestTS ]

        # finally, write the new data point to the data file
        try:
            # insist on getting data in dictionary format
            assert type(data) is dict;

            # figure out if the data file has already been written to
            fileExists = (path.isfile(self.__logData) and path.getsize(self.__logData) > 0)

            # figure out if this record is more than just a timestamp
            realData = (len([x for x in data if 'Timestamp' not in x]) > 0)

            # don't bother writing if file doesn't exist and there's no real data
            # (because you won't be able to provide a full list of headers)
            if fileExists or realData:

                # write to the data file
                with open(self.__logData, 'a', newline='') as f:

                    w = DictWriter(f, fieldnames=data.keys(), dialect='unix')

                    # write out the header if this is an empty/nonexistent file
                    if not fileExists:
                        w.writeheader()

                    # write the new data row
                    w.writerow(data)

                    # don't buffer the output stream, in case of irregular app termination
                    f.flush()

                    # force python to write changes to disk (windows)
                    if _fsyncLoaded:
                        fsync(f.fileno())

                # force python to write changes to disk (non-windows)
                if _syncLoaded:
                    sync()

        except Exception as e:
            print (f'{self.__class__.__name__}: Error: writeData(): {str(e)}')

    def writeMessage(self, *args):
        try:
            # the current time
            clock = dt.now(tz=tz.utc)

            # create a list starting with the current timestamp
            writeList = [clock.strftime(self.__dtFormat),
                         clock.astimezone(self.__timezone).strftime(self.__dtFormat) ]

            # add whatever parameters were passed
            if len(args) > 0:
                writeList.extend(args)

            # write to the messages file
            with open(self.__logMessages, 'a', newline='') as f:
                w = writer(f, dialect='unix')
                w.writerow(writeList)

                # don't buffer the output stream, in case of irregular app termination
                f.flush()

                # force python to write changes to disk (windows)
                if _fsyncLoaded:
                    fsync(f.fileno())

            # force python to write changes to disk (non-windows)
            if _syncLoaded:
                sync()

        except Exception as e:
            print (f'{self.__class__.__name__}: Error: __writeMessage({str(args)}): {str(e)}')

    def logDir(self):

        return self.__logDir

    def exportLog(self, reqTS=None):

        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): earliest  [{self.earliestTS}]")
        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): latest    [{self.latestTS}]")
        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): requested [{reqTS}]")

        # what is the oldest timestamp still in memory (if any)?
        if len(self.history) > 0:
            memTS = self.strToUtcDatetime(self.history[0]['Timestamp.UTC'])
        else:
            memTS = None

        # my assumption is that earliestTS and latestTS are either both None or both not None
        assert (self.earliestTS is None and self.latestTS is None) or (self.earliestTS is not None and self.latestTS is not None)

        # assume we need to pull history from disk, and then check for cases where we don't
        pullFromDisk = True

        # no logs at all, so nothing to load
        if self.earliestTS is None:
            pullFromDisk = False

        # for the rest of this logic we can assume that earliestTS and latestTS are not None

        # requested TS is later than all our history, so don't bother loading
        elif (reqTS is not None and reqTS > self.latestTS):
            pullFromDisk = False

        # oldest in memory is same-or-older than requested TS, so memory data can satisfy this request
        elif (reqTS is not None and (memTS is not None and memTS <= reqTS)):
            pullFromDisk = False

        # requested TS is None (give me everything) but there's nothing on disk that isn't also in memory
        elif (reqTS is None and (memTS is not None and memTS <= self.earliestTS)):
            pullFromDisk = False

        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): pullFromDisk [{pullFromDisk}]")

        # default to nothing
        answerLog = []

        # start with everything
        if pullFromDisk:

            # are there any data records to be read in?
            if path.isfile(self.__logData) and path.getsize(self.__logData) > 0:

                # try to read in the old data to memory
                with open(self.__logData, 'r', newline='') as f:

                    # use "generator" syntax to strip out NULLs and drop blank lines
                    lines = (x.replace('\x00','') for x in f if x.replace('\x00','') != '')

                    # pass the generator along to DictReader, and convert to list
                    r = DictReader(lines, dialect='unix')
                    answerLog = list(r)

        else:
            answerLog = self.history.copy()

        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): before filtering [{len(answerLog)}]")

        # delete any historical data older than the requested TS (if any)
        if reqTS is not None:
            answerLog = [ x for x in answerLog if self.strToUtcDatetime(x['Timestamp.UTC']) > reqTS ]

        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): after filtering [{len(answerLog)}]")

        # and that's your answer
        return answerLog

    def importLog(self, newLog=None):

        # nothing to do if additional log is empty
        if newLog is not None and len(newLog) > 0:

            # figure out earliest and latest TS of new information
            newEarliestTS = self.strToUtcDatetime(newLog[0]['Timestamp.UTC'])
            newLatestTS = self.strToUtcDatetime(newLog[len(newLog)-1]['Timestamp.UTC'])

            # check assumptions
            if newEarliestTS > newLatestTS:
                print (f'{self.__class__.__name__}: Error: importLog data are out of order')
            elif self.latestTS is not None and self.latestTS > newLatestTS:
                print (f'{self.__class__.__name__}: Error: importLog data are earlier than loaded history')
            else:

                # if any data are older than what's already stored, filter them out
                if self.latestTS is not None and self.latestTS > newEarliestTS:
                    newLog = [ x for x in newLog if self.strToUtcDatetime(x['Timestamp.UTC']) > self.latestTS ]

                # check again if there are any new records to add
                if len(newLog) > 0 :

                    # first, add the new records to the in-memory storage
                    self.history.extend(newLog)

                    # update earliest and latest TS if necessary
                    if self.earliestTS is None:
                        self.earliestTS = newEarliestTS
                    if self.latestTS is None or self.latestTS < newLatestTS:
                        self.latestTS = newLatestTS

                    # write these new records to the file
                    # finally, write the new data point to the data file
                    try:
                        # figure out if the data file has already been written to
                        fileExists = (path.isfile(self.__logData) and path.getsize(self.__logData) > 0)

                        # write to the data file
                        with open(self.__logData, 'a', newline='') as f:

                            w = DictWriter(f, fieldnames=newLog[0].keys(), dialect='unix')

                            # write out the header if this is an empty/nonexistent file
                            if not fileExists:
                                w.writeheader()

                            # write the new data rows
                            w.writerows(newLog)

                            # don't buffer the output stream, in case of irregular app termination
                            f.flush()

                            # force python to write changes to disk (windows)
                            if _fsyncLoaded:
                                fsync(f.fileno())

                        # force python to write changes to disk (non-windows)
                        if _syncLoaded:
                            sync()

                    except Exception as e:
                        print (f'{self.__class__.__name__}: Error: importLog(): {str(e)}')

                    # calculate the oldest timestamp that should be kept in memory
                    oldestTS = dt.now(tz=tz.utc) - td(seconds=self.__memoryRetention)

                    # delete any historical data older than the retention timeframe
                    self.history = [ x for x in self.history if self.strToUtcDatetime(x['Timestamp.UTC']) > oldestTS ]

                    # last step: any new log imports should trigger a rewrite of the summary log files
                    self.rewriteSummaries(newLog)

    def rewriteSummaries(self, newLog):

        # this should only ever be called for device logs
        assert(self.__logType == 'device')

        # keep an eye on how much time this is all taking
        beginTime = dt.now(tz=tz.utc)

        # figure out earliest and latest TS of new information
        rewriteEarliestTS = self.strToUtcDatetime(newLog[0]['Timestamp.UTC'])
        rewriteLatestTS = self.strToUtcDatetime(newLog[len(newLog)-1]['Timestamp.UTC'])

        # load up the summary log state if it's not already loaded
        if 'summaryLogState' not in self.erl2context:
            self.erl2context['summaryLogState'] = Erl2State(internalID='summaryLog', erl2context=self.erl2context)

        # check if this device is already in the summary logs
        timing = self.erl2context['summaryLogState'].get(self.__logHeader, 'timing', {})

        # get the full list of devices already in the summary file
        allDevices = self.erl2context['summaryLogState'].allTypes()

        # complicated sort to properly order e.g. 'Tank 2' before 'Tank 13'
        allDevices = sorted(allDevices, key=lambda x: re_sub(r'0*([0-9]{9,})', r'\1', re_sub(r'([0-9]+)', r'0000000000\1', x)))

        # if this device isn't in the logs yet, rewrite all logs back to its oldest log record
        if 'startTS' not in timing or 'endTS' not in timing:
            rewriteEarliestTS = self.earliestTS
            rewriteLatestTS = self.latestTS

            #print (f"{__class__.__name__}: Debug: rewriteSummaries({self.__logHeader}): CREATING [{rewriteEarliestTS}][{rewriteLatestTS}]")

        ## otherwise, just rewrite all logs back to where this newLog begins
        #else:
        #    print (f"{__class__.__name__}: Debug: rewriteSummaries({self.__logHeader}): ADDING [{rewriteEarliestTS}][{rewriteLatestTS}]")

        # convert to rounded timestamps
        ts1 = self.roundedTimestamp(rewriteEarliestTS)
        ts2 = self.roundedTimestamp(rewriteLatestTS)

        # do we need to read in this device's data history from disk?
        deviceData = newLog
        if ts1 < self.strToUtcDatetime(self.history[0]['Timestamp.UTC']).timestamp():

            # try to read in the old data to memory
            with open(self.__logData, 'r', newline='') as f:

                # use "generator" syntax to strip out NULLs and drop blank lines
                lines = (x.replace('\x00','') for x in f if x.replace('\x00','') != '')

                # pass the generator along to DictReader, and convert to list
                r = DictReader(lines, dialect='unix')
                deviceData = list(r)

        # I think I want to turn this into a dict keyed by (rounded) UTC timestamps
        deviceDict = {}
        for dline in deviceData:

            # calculate timestamp and round it
            deviceTS = self.strToUtcDatetime(dline['Timestamp.UTC']).timestamp()
            roundedTS = self.roundedTimestamp(deviceTS)
            diffTS = abs(deviceTS-roundedTS)

            # if more than one line rounds to the same TS, choose the one that is closest
            if roundedTS not in deviceDict or diffTS < deviceDict[roundedTS]['diffTS']:
                deviceDict[roundedTS] = {'diffTS':diffTS, 'dataLine':dline}

        # JIC memory is a problem
        del deviceData

        # loop through subSystems!
        for sys in SUBSYSTEMS:

            # loop variables for the main loop
            oldFileHandle = newFileHandle = oldReader = fileYYYYMM = oldLine = oldTime = None
            finishedWriting = headerWritten = oldLineWaiting = False
            thisTS = ts1

            # now the main action: loop through every timepoint in the range whether we have data or not
            while not finishedWriting:

                # determine year and month
                thisYYYYMM = dt.fromtimestamp(thisTS).astimezone(tz.utc).strftime('%Y/%m')

                # need to open (different) input/output summary log files?
                if fileYYYYMM is None or fileYYYYMM != thisYYYYMM:
                    fileYYYYMM = thisYYYYMM

                    # create summary log directories if need be
                    makedirs(f"{self.__summaryDir}/{fileYYYYMM}", exist_ok=True)

                    # close any prior oldFileHandles
                    if oldFileHandle is not None and not oldFileHandle.closed:
                        oldFileHandle.close()
                        oldReader = None

                    # close any prior newFileHandles
                    if newFileHandle is not None and not newFileHandle.closed:
                        newFileHandle.close()

                        # force python to write changes to disk (non-windows)
                        if _syncLoaded:
                            sync()

                    # what is the full filename?
                    fnMonth = dt.fromtimestamp(thisTS).astimezone(tz.utc).strftime('%Y-%m')
                    fn = f"{self.__summaryDir}/{fileYYYYMM}/{sys}-{fnMonth}.csv"

                    # if it exists, rename the old file instead of overwriting
                    if path.isfile(fn) and path.getsize(fn) > 0:
                        moveFile(fn, fn + '.bak')

                        # open the old file for reading
                        oldFileHandle = open(fn + '.bak', 'r') #, newline='')

                        # create a DictReader instance for it
                        oldReader = DictReader(oldFileHandle,dialect='unix')

                    # open the new file for writing
                    newFileHandle = open(fn, 'w', newline='')
                    headerWritten = None

                # load the next record from the old summary log, if any
                if oldReader is not None and not oldLineWaiting:

                    # keep looping until a valid line is found, or no more lines
                    while True:

                        # try to get another line
                        oldLine = next(oldReader,None)

                        # no more lines
                        if oldLine is None:
                            oldTime = None
                            break

                        # valid line found?
                        if 'Timestamp.UTC' in oldLine:
                            oldTime = self.roundedTimestamp(oldLine['Timestamp.UTC'])
                            oldLineWaiting = True
                            break

                        # otherwise we found a line that wasn't valid, so keep going

                # determine what timestamp to output (old summary record, new data record, or both)
                outputTS = thisTS
                if oldTime is not None and oldTime <= outputTS:
                    outputTS = oldTime
                    oldLineWaiting = False

                # get a datetime instance for the timestamp we're writing out
                outputDate = dt.fromtimestamp(outputTS).astimezone(tz.utc)

                # create the output dict
                outputDict = {'Timestamp.UTC':outputDate.strftime(self.__dtFormat),
                              'Timestamp.Local':outputDate.astimezone(self.__timezone).strftime(self.__dtFormat)}

                # loop through all devices represented in this summary
                for dev in allDevices:
                    # do we have new data for this device?
                    if (    dev == self.__logHeader
                        and outputTS in deviceDict
                        and 'dataLine' in deviceDict[outputTS]
                        and 's.'+sys in deviceDict[outputTS]['dataLine']
                        and deviceDict[outputTS]['dataLine']['s.'+sys] is not None):

                        outputDict[dev] = deviceDict[outputTS]['dataLine']['s.'+sys]

                    # do we have old data for this device?
                    elif (    oldTime is not None
                          and oldTime == outputTS
                          and oldLine is not None
                          and dev in oldLine
                          and oldLine[dev] is not None):

                        outputDict[dev] = oldLine[dev]

                    # otherwise leave it blank
                    else:
                        outputDict[dev] = None

                # write this line to the output file
                w = DictWriter(newFileHandle, fieldnames=outputDict.keys(), dialect='unix')

                # write out the header if it hasn't been written yet
                if not headerWritten:
                    w.writeheader()
                    headerWritten = True

                # write the new data row
                w.writerow(outputDict)

                # don't buffer the output stream, in case of irregular app termination
                newFileHandle.flush()

                # force python to write changes to disk (windows)
                if _fsyncLoaded:
                    fsync(newFileHandle.fileno())

                # if we've written a record for thisTS, increment it
                if outputTS == thisTS:
                    thisTS += self.__systemFrequency

                # stop looping if we've run out of both new and old records
                if thisTS > ts2 and not oldLineWaiting:
                    finishedWriting = True

            # cleanup: close any still-open files
            if oldFileHandle is not None and not oldFileHandle.closed:
                oldFileHandle.close()
                oldReader = None

            if newFileHandle is not None and not newFileHandle.closed:
                newFileHandle.close()

                # force python to write changes to disk (non-windows)
                if _syncLoaded:
                    sync()

        # update the summary log state with new timing
        self.erl2context['summaryLogState'].set([(self.__logHeader, 'timing', {'startTS':self.earliestTS, 'endTS':self.latestTS})])

        # keep an eye on how much time this is all taking
        endTime = dt.now(tz=tz.utc)

        print (f"{__class__.__name__}: [{endTime}]: Debug: rewriteSummaries({self.__logHeader}, " +
               f"[{rewriteEarliestTS.astimezone(self.__timezone).strftime(self.__dtFormat)}], " +
               f"[{rewriteLatestTS.astimezone(self.__timezone).strftime(self.__dtFormat)}]): " +
               f"time elapsed [{endTime.timestamp()-beginTime.timestamp()}]")

    def strToUtcDatetime(self, s):

        return dt.strptime(s, self.__dtFormat).replace(tzinfo=tz.utc)

    def roundedTimestamp(self, ts):

        # if passed a str, assume this is a formatted date string
        if type(ts) is str:
            return float(round(self.strToUtcDatetime(ts).timestamp() / self.__systemFrequency)) * self.__systemFrequency

        # if passed a datetime
        elif type(ts) is dt:
            return float(round(ts.timestamp() / self.__systemFrequency)) * self.__systemFrequency

        # if passed a float (i.e. already a timestamp)
        elif type(ts) is float:
            return float(round(ts / self.__systemFrequency)) * self.__systemFrequency

        # otherwise, unexpected
            print (f"{self.__class__.__name__}: Warning: roundedTimestamp passed type [{type(ts).__name__}]")
            return None

def main():

    log = Erl2Log()
    print ("Erl2Log module (no GUI)")

if __name__ == "__main__": main()

