from csv import DictReader,DictWriter,writer
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz
from os import makedirs,path,stat
from sys import version_info
from Erl2Config import Erl2Config

class Erl2Log():

    # remember what kinds of logs have already been instantiated
    logTypes = {}

    def __init__(self, logType='generic', logName='generic', erl2context={}):
        self.__logType = logType
        self.__logName = logName
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

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
        try:
            # if there's no system-level log, reroute to a debug directory
            if 'system' not in Erl2Log.logTypes:
                self.__logDir = self.erl2context['conf']['system']['logDir'] + '/zDebug/' + self.__logType
            else:
                self.__logDir = self.erl2context['conf']['system']['logDir'] + '/' + self.__logType

        except Exception as e:
            print (f"{self.__class__.__name__}: Error: Could not determine location of main logging directory: {e}")
            raise

        # internal attributes
        self.__logMessages = self.__logDir + '/' + self.__logName + '.txt'
        self.__logData = self.__logDir + '/' + self.__logName + '.dat'

        # initial directories
        if not path.isdir(self.erl2context['conf']['system']['logDir']):
            makedirs(self.erl2context['conf']['system']['logDir'])
        if not path.isdir(self.__logDir):
            makedirs(self.__logDir)

        # # initial messaging
        # self.writeMessage(f'{self.__class__.__name__}[{self.__logType}][{self.__logName}]: log initialized')

        # are there any data records to be read in?
        if path.isfile(self.__logData) and stat(self.__logData).st_size > 0:

            # try to read in the old data to memory
            with open(self.__logData, 'r', newline='') as f:

                # use "generator" syntax to strip out NULLs and drop blank lines
                lines = (x.replace('\x00','') for x in f if x.replace('\x00','') != '')

                # pass the generator along to DictReader, and convert to list
                r = DictReader(lines, dialect='unix')
                self.history = list(r)

            # make a note of the earliest and latest timestamps in the history file, before trimming what's kept in memory
            if len(self.history) > 0:
                ts = dt.strptime(self.history[0]['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc)
                if self.earliestTS is None or ts < self.earliestTS:
                    self.earliestTS = ts
                    #print (f"{__class__.__name__}: Debug: __init__({self.__logType},{self.__logName}): self.earliestTS [{self.earliestTS}]")

                ts = dt.strptime(self.history[len(self.history)-1]['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc)
                if self.latestTS is None or ts < self.latestTS:
                    self.latestTS = ts
                    #print (f"{__class__.__name__}: Debug: __init__({self.__logType},{self.__logName}): self.latestTS [{self.latestTS}]")

            # calculate the oldest timestamp that should be kept in memory
            oldestTS = dt.now(tz=tz.utc) - td(seconds=self.erl2context['conf']['system']['memoryRetention'])

            # delete any historical data older than the retention timeframe
            self.history = [ x for x in self.history if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc) > oldestTS ]

        # # make a note if we've reloaded anything from memory
        # if len(self.history) > 0:
        #     self.writeMessage(f'{self.__class__.__name__}[{self.__logType}][{self.__logName}]: loaded [{len(self.history)}] record(s) from existing data files')

    def writeData(self, data):

        # see if earliest or latest timestamps need to be updated
        if 'Timestamp.UTC' in data:
            ts = dt.strptime(data['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc)
            if self.earliestTS is None or ts < self.earliestTS:
                self.earliestTS = ts
                #print (f"{__class__.__name__}: Debug: writeData({self.__logType},{self.__logName}): self.earliestTS [{self.earliestTS}]")
            if self.latestTS is None or ts > self.latestTS:
                self.latestTS = ts
                #print (f"{__class__.__name__}: Debug: writeData({self.__logType},{self.__logName}): self.latestTS [{self.latestTS}]")

        # first, add the new data point to in-memory history
        self.history.append(data)

        # calculate the oldest timestamp that should be kept in memory
        oldestTS = dt.now(tz=tz.utc) - td(seconds=self.erl2context['conf']['system']['memoryRetention'])

        # delete any historical data older than the retention timeframe
        self.history = [ x for x in self.history if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc) > oldestTS ]

        # finally, write the new data point to the data file
        try:
            # insist on getting data in dictionary format
            assert type(data) is dict;

            # figure out if the data file has already been written to
            fileExists = (path.isfile(self.__logData) and stat(self.__logData).st_size > 0)

            # figure out if this record is more than just a timestamp
            realData = (len([x for x in data if 'Timestamp' not in x]) > 0)

            # don't bother writing if file doesn't exist and there's no real data
            # (because you won't be able to provide a full list of headers)
            if fileExists or realData:

                # write to the data file
                with open(self.__logData, 'a', newline='') as f:

                    #w = DictWriter(f, fieldnames=data.keys(), lineterminator='\n')
                    w = DictWriter(f, fieldnames=data.keys(), dialect='unix')

                    # write out the header if this is an empty/nonexistent file
                    if not fileExists:
                        w.writeheader()

                    # write the new data row
                    w.writerow(data)

                    # don't buffer the output stream, in case of irregular app termination
                    f.flush()

        except Exception as e:
            print (f'{self.__class__.__name__}: Error: writeData(): {str(e)}')

    def writeMessage(self, *args):
        try:
            # the current time
            clock = dt.now(tz=tz.utc)

            # create a list starting with the current timestamp
            writeList = [clock.strftime(self.erl2context['conf']['system']['dtFormat']),
                         clock.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']) ]

            # add whatever parameters were passed
            if len(args) > 0:
                writeList.extend(args)

            # write to the messages file
            with open(self.__logMessages, 'a', newline='') as f:
                #w = writer(f, lineterminator='\n')
                w = writer(f, dialect='unix')
                w.writerow(writeList)

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
            memTS = dt.strptime(self.history[0]['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc)
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
            if path.isfile(self.__logData) and stat(self.__logData).st_size > 0:

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
            answerLog = [ x for x in answerLog if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc) > reqTS ]

        #print (f"{__class__.__name__}: Debug: exportLog({self.__logType},{self.__logName}): after filtering [{len(answerLog)}]")

        # and that's your answer
        return answerLog

    def importLog(self, newLog=None):

        # nothing to do if additional log is empty
        if newLog is not None and len(newLog) > 0:

            # figure out earliest and latest TS of new information
            newEarliestTS = dt.strptime(newLog[0]['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc)
            newLatestTS = dt.strptime(newLog[len(newLog)-1]['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc)

            # check assumptions
            if newEarliestTS > newLatestTS:
                print (f'{self.__class__.__name__}: Error: importLog data are out of order')
            elif self.latestTS is not None and self.latestTS > newLatestTS:
                print (f'{self.__class__.__name__}: Error: importLog data are earlier than loaded history')
            else:

                # if any data are older than what's already stored, filter them out
                if self.latestTS is not None and self.latestTS > newEarliestTS:
                    newLog = [ x for x in newLog if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc) > self.latestTS ]

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
                        fileExists = (path.isfile(self.__logData) and stat(self.__logData).st_size > 0)

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

                    except Exception as e:
                        print (f'{self.__class__.__name__}: Error: importLog(): {str(e)}')

                    # calculate the oldest timestamp that should be kept in memory
                    oldestTS = dt.now(tz=tz.utc) - td(seconds=self.erl2context['conf']['system']['memoryRetention'])

                    # delete any historical data older than the retention timeframe
                    self.history = [ x for x in self.history if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).replace(tzinfo=tz.utc) > oldestTS ]

    # not a class method but just a useful calculation
    def nextIntervalTime(currentTime, interval):

        retval = (
                   (
                     int(
                       currentTime.timestamp() # timestamp in seconds
                       / interval              # convert to number of intervals of length loggingFrequency
                     )                         # truncate to beginning of previous interval (past)
                   + 1)                        # advance by one time interval (future)
                   * interval                  # convert back to seconds/timestamp
                 )

        return retval

def main():

    log = Erl2Log()
    print ("Erl2Log module (no GUI)")

if __name__ == "__main__": main()

