#! /usr/bin/python3

import csv
import datetime
import os
import sys
from Erl2Config import Erl2Config

class Erl2Log():

    def __init__(self, logType='system', logName='default', config=None):
        self.__logType = logType
        self.__logName = logName
        self.config = config

        # we'll keep a certain number of measurements resident in-memory for plotting
        self.history = []

        # this module requires Python 3.7 or higher
        # (the release when dictionaries are guaranteed to be ordered)
        try:
            assert sys.version_info > (3,7)
        except:
            print("Erl2Log: Python 3.7 or higher is required for this system")
            raise

        # read in the system configuration file if needed
        if self.config is None:
            self.config = Erl2Config()
            if 'tank' in self.config.sections() and 'id' in self.config['tank']:
                print (f"Erl2Log: Tank Id is [{self.config['tank']['id']}]")

        # determine location of main logging directory
        try:
            self.__logDir = self.config['system']['logDir'] + '/' + self.__logType
        except Exception as e:
            print(f"Erl2Log: Could not determine location of main logging directory: {e}")
            raise

        # internal attributes
        self.__logMessages = self.__logDir + '/' + self.__logName + '.txt'
        self.__logData = self.__logDir + '/' + self.__logName + '.dat'

        # initial directories
        if not os.path.isdir(self.config['system']['logDir']):
            os.makedirs(self.config['system']['logDir'])
        if not os.path.isdir(self.__logDir):
            os.makedirs(self.__logDir)

        # initial messaging
        self.writeMessage(f'Erl2Log[{self.__logType}][{self.__logName}]: log initialized')

        # are there any data records to be read in?
        if os.path.isfile(self.__logData) and os.stat(self.__logData).st_size > 0:

            # try to read in the old data to memory
            with open(self.__logData, 'r', newline='') as f:
                r = csv.DictReader(f, dialect='unix')
                self.history = list(r)

            # calculate the oldest timestamp that should be kept in memory
            oldest = datetime.datetime.utcnow().timestamp() - self.config['temperature']['sampleRetention']

            # delete any historical data older than the retention timeframe
            self.history = [ x for x in self.history if datetime.datetime.strptime(x['Timestamp'], self.config['system']['dtFormat']).timestamp() > oldest ]

        # make a note if we've reloaded anything from memory
        if len(self.history) > 0:
            self.writeMessage(f'Erl2Log[{self.__logType}][{self.__logName}]: loaded [{len(self.history)}] record(s) from existing data files')

    def writeData(self, data):

        # first, add the new data point to in-memory history
        self.history.append(data)

        # calculate the oldest timestamp that should be kept in memory
        oldest = datetime.datetime.utcnow().timestamp() - self.config['temperature']['sampleRetention']

        # delete any historical data older than the retention timeframe
        self.history = [ x for x in self.history if datetime.datetime.strptime(x['Timestamp'], self.config['system']['dtFormat']).timestamp() > oldest ]

        # finally, write the new data point to the data file
        try:
            # insist on getting data in dictionary format
            assert type(data) is dict;

            # figure out if the data file has already been written to
            fileExists = (os.path.isfile(self.__logData) and os.stat(self.__logData).st_size > 0)

            # write to the data file
            with open(self.__logData, 'a', newline='') as f:

                #w = csv.DictWriter(f, fieldnames=data.keys(), lineterminator='\n')
                w = csv.DictWriter(f, fieldnames=data.keys(), dialect='unix')

                # write out the header if this is an empty/nonexistent file
                if not fileExists:
                    w.writeheader()

                # write the new data row
                w.writerow(data)

        except Exception as e:
            print(f'Debug Erl2Log.__writeData() error: {str(e)}')

    def writeMessage(self, *args):
        try:
            # create a list starting with the current timestamp
            writeList = [datetime.datetime.utcnow().strftime(self.config['system']['dtFormat'])]

            # add whatever parameters were passed
            if len(args) > 0:
                writeList.extend(args)

            # write to the messages file
            with open(self.__logMessages, 'a', newline='') as f:
                #w = csv.writer(f, lineterminator='\n')
                w = csv.writer(f, dialect='unix')
                w.writerow(writeList)

        except Exception as e:
            print(f'Debug Erl2Log.__writeMessage({str(args)}) error: {str(e)}')
