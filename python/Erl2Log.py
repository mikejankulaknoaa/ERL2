#! /usr/bin/python3

from csv import DictReader,DictWriter,writer
from datetime import datetime as dt
from datetime import timezone as tz
from os import makedirs,path,stat
from sys import version_info
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config

class Erl2Log():

    def __init__(self, logType='system', logName='default', erl2context={}):
        self.__logType = logType
        self.__logName = logName
        self.erl2context = erl2context

        # we'll keep a certain number of measurements resident in-memory for plotting
        self.history = []

        # this module requires Python 3.7 or higher
        # (the release when dictionaries are guaranteed to be ordered)
        try:
            assert version_info > (3,7)
        except:
            print (f"{self.__class__.__name__}: Error: Python 3.7 or higher is required for this system")
            raise

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # determine location of main logging directory
        try:
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
                r = DictReader(f, dialect='unix')
                self.history = list(r)

            # calculate the oldest timestamp that should be kept in memory
            oldest = dt.now(tz=tz.utc).timestamp() - self.erl2context['conf'][self.__logName]['memoryRetention']

            # delete any historical data older than the retention timeframe
            self.history = [ x for x in self.history if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).timestamp() > oldest ]

        # # make a note if we've reloaded anything from memory
        # if len(self.history) > 0:
        #     self.writeMessage(f'{self.__class__.__name__}[{self.__logType}][{self.__logName}]: loaded [{len(self.history)}] record(s) from existing data files')

    def writeData(self, data):

        # first, add the new data point to in-memory history
        self.history.append(data)

        # calculate the oldest timestamp that should be kept in memory
        oldest = dt.now(tz=tz.utc).timestamp() - self.erl2context['conf'][self.__logName]['memoryRetention']

        # delete any historical data older than the retention timeframe
        self.history = [ x for x in self.history if dt.strptime(x['Timestamp.UTC'], self.erl2context['conf']['system']['dtFormat']).timestamp() > oldest ]

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

        except Exception as e:
            print (f'{self.__class__.__name__}: Error: __writeData(): {str(e)}')

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

def main():

    root = tk.Tk()
    log = Erl2Log()
    root.mainloop()

if __name__ == "__main__": main()

