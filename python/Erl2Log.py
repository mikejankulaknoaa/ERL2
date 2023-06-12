#! /usr/bin/python3

import csv
import datetime
import os

ONEDAY = 86400
LOGDIR = os.getcwd() + '/log'

class Erl2Log():

    def __init__(self, logType='system', logName='default'):
        self.__logType = logType
        self.__logName = logName

        # internal attributes
        self.__logDir = LOGDIR + '/' + self.__logType
        self.__logMessages = self.__logDir + '/' + self.__logName + '.txt'
        self.__logData = self.__logDir + '/' + self.__logName + '.dat'
        self.__memFrequency = 5
        self.__memRetention = ONEDAY
        self.__memNextWrite = None
        self.__fileFrequency = 300.
        self.__fileRetention = None
        self.__fileNextWrite = None

        # initial directories
        if not os.path.isdir(LOGDIR):
            os.makedirs(LOGDIR)
        if not os.path.isdir(self.__logDir):
            os.makedirs(self.__logDir)

        # initial messaging
        #print(f'Erl2Log.__init__: writing first message')
        self.writeMessage('Log initialized')

    def writeMessage(self, *args):
        # always write messages when asked
        self.__writeAll(self.__logMessages, args)

    def writeData(self, *args):
        # grab a timestamp
        tStamp = datetime.datetime.utcnow().timestamp()

        # check timing to see if we want to write anything to file
        if (self.__fileNextWrite is None) or (tStamp >= self.__fileNextWrite):
            # write to file 
            self.__writeAll(self.__logData, args)

            # figure out when next record should be written
            self.__fileNextWrite = (int(tStamp/self.__fileFrequency)+1.)*self.__fileFrequency

    def __writeAll(self, file, fields):
        #print(f'Erl2Log.__writeAll({file},{str(fields)})')
        try:
            # create a list starting with the current timestamp
            writeList = [str(datetime.datetime.utcnow())]

            # add whatever parameters were passed
            if len(fields) > 0:
                writeList.extend(fields)

            # write to the appropriate file
            with open(file, 'a', newline='') as f:
                w = csv.writer(f)
                w.writerow(writeList)

        except Exception as e:
            print(f'Debug Erl2Log.__writeAll({file},{str(fields)}) error: {str(e)}')
