#! /usr/bin/python3

import ast
import os
from configparser import ConfigParser

class Erl2Config():

    def __init__(self):

        # initialize configuration object that reads in erl2.conf parameters
        in_conf = ConfigParser()

        # initialize internal parameter dictionary
        self.__conf = {}
        self.__conf['system'] = {}
        self.__conf['tank'] = {}
        self.__conf['temperature'] = {}
        self.__conf['pH'] = {}

        # the python source file that is currently executing
        thisFile = os.path.realpath(__file__)

        # the directory holding the currently executing source file
        parent = os.path.dirname(thisFile)

        # look for erl2.conf in its parent directories one by one
        loop = 0
        while (True):

            # found a file named erl2.conf !
            if os.path.exists(parent + '/erl2.conf'): 
                self.__conf['system']['rootDir'] = parent
                self.__conf['system']['confFile'] = parent + '/erl2.conf'
                print (f"Erl2Config: debug: found root directory {self.__conf['system']['rootDir']}")
                print (f"Erl2Config: debug: found configuration file {self.__conf['system']['confFile']}")
                break

            # give up if there are no higher directories to check
            if parent == os.path.dirname(parent):
                break

            # next time through the loop, look one level higher up
            parent = os.path.dirname(parent)

            # avoid infinite looping
            loop += 1
            if loop > 100:
                break

        # if we found a configuration file
        if 'confFile' in self.__conf['system']:

            # read and parse the config file
            in_conf.read(self.__conf['system']['confFile'])

        # otherwise we couldn't find a config
        else:
            raise RuntimeError('Cannot find the erl2.conf configuration file')

        # explicitly define a datetime format to ensure reading/writing is consistent
        # (this one cannot be customized in the erl2.conf file)
        self.__conf['system']['dtFormat'] = '%Y-%m-%d %H:%M:%S.%f'

        # special logic for validating the main log directory
        if 'logDir' not in in_conf['system']:
            self.__conf['system']['logDir'] = self.__conf['system']['rootDir'] + '/log'
        else:
            self.__conf['system']['logDir'] = in_conf['system']['logDir']

        # we must insist that the parent of the specified directory already exists, at least
        if not os.path.isdir(os.path.dirname(self.__conf['system']['logDir'])):
            raise TypeError(f"Erl2Config: ['system']['logDir'] = [{self.__conf['system']['logDir']}] is not a valid directory")

        # here is where we will define default values for key parameters,
        # in case any crucial values are missing from the erl2.conf file.
        # we are also doing some type-checking at the same time.

        # system

        if 'fileLogging' not in in_conf['system']:
            in_conf['system']['fileLogging'] = 'True'
        try:
            self.__conf['system']['fileLogging'] = in_conf.getboolean('system','fileLogging')
        except:
            raise TypeError(f"Erl2Config: ['system']['fileLogging'] = [{in_conf['system']['fileLogging']}] is not boolean")

        # tank

        if 'id' not in in_conf['tank']:
            in_conf['tank']['id'] = 'Tank 0'
        self.__conf['tank']['id'] = in_conf['tank']['id']

        # temperature

        if 'enabled' not in in_conf['temperature']:
            in_conf['temperature']['enabled'] = 'True'
        try:
            self.__conf['temperature']['enabled'] = in_conf.getboolean('temperature','enabled')
        except:
            raise TypeError(f"Erl2Config: ['temperature']['enabled'] = [{in_conf['temperature']['enabled']}] is not boolean")

        if 'sampleFrequency' not in in_conf['temperature']:
            in_conf['temperature']['sampleFrequency'] = '5'
        try:
            self.__conf['temperature']['sampleFrequency'] = int(in_conf['temperature']['sampleFrequency'])
            if self.__conf['temperature']['sampleFrequency'] <= 0:
                raise TypeError
        except:
            raise TypeError(f"Erl2Config: ['temperature']['sampleFrequency'] = [{self.conf['temperature']['sampleFrequency']}] is not a positive integer")

        if 'sampleRetention' not in in_conf['temperature']:
            in_conf['temperature']['sampleRetention'] = '86400'
        try:
            self.__conf['temperature']['sampleRetention'] = int(in_conf['temperature']['sampleRetention'])
            if self.__conf['temperature']['sampleRetention'] <= 0:
                raise TypeError
        except:
            raise TypeError(f"Erl2Config: ['temperature']['sampleRetention'] = [{self.conf['temperature']['sampleRetention']}] is not a positive integer")

        if 'loggingFrequency' not in in_conf['temperature']:
            in_conf['temperature']['loggingFrequency'] = '300'
        try:
            self.__conf['temperature']['loggingFrequency'] = int(in_conf['temperature']['loggingFrequency'])
            if self.__conf['temperature']['loggingFrequency'] <= 0:
                raise TypeError
        except:
            raise TypeError(f"Erl2Config: ['temperature']['loggingFrequency'] = [{self.conf['temperature']['loggingFrequency']}] is not a positive integer")

        if 'validRange' not in in_conf['temperature']:
            in_conf['temperature']['validRange'] = '[10.0, 40.0]'
        try:
            # convert a string that looks like a Python list into an actual Python list
            self.__conf['temperature']['validRange'] = ast.literal_eval(in_conf['temperature']['validRange'])
            if (type(self.__conf['temperature']['validRange']) is not list
                    or len (self.__conf['temperature']['validRange']) != 2):
                raise
            # explicitly convert integers to floats
            self.__conf['temperature']['validRange'] = [ float(x) if type(x) is int else x for x in self.__conf['temperature']['validRange'] ]
            if len([ x for x in self.__conf['temperature']['validRange'] if type(x) is not float ]) > 1:
                raise
        except:
            raise TypeError(f"Erl2Config: ['temperature']['validRange'] = [{in_conf['temperature']['validRange']}] is not a list of 2 floats")


        if 'setpointDefault' not in in_conf['temperature']:
            in_conf['temperature']['setpointDefault'] = '25.0'
        try:
            self.__conf['temperature']['setpointDefault'] = float(in_conf['temperature']['setpointDefault'])
            # check value against min/max in valid temperature range
            if (self.__conf['temperature']['setpointDefault'] < self.__conf['temperature']['validRange'][0]
                    or self.__conf['temperature']['setpointDefault'] > self.__conf['temperature']['validRange'][1]):
                raise
        except:
            raise TypeError(f"Erl2Config: ['temperature']['setpointDefault'] = [{in_conf['temperature']['setpointDefault']}] is not a float within the valid range for this sensor")

        if 'offsetDefault' not in in_conf['temperature']:
            in_conf['temperature']['offsetDefault'] = '0.1'
        try:
            self.__conf['temperature']['offsetDefault'] = float(in_conf['temperature']['offsetDefault'])
            if self.__conf['temperature']['offsetDefault'] <= 0.:
                raise
        except:
            raise TypeError(f"Erl2Config: ['temperature']['offsetDefault'] = [{in_conf['temperature']['offsetDefault']}] is not a positive float")


        if 'dynamicDefault' not in in_conf['temperature']:
            in_conf['temperature']['dynamicDefault'] = ('[27.0, 26.5, 26.0, 25.6, 25.3, 25.1, '
                                                        '25.0, 25.1, 25.3, 25.6, 26.0, 26.5, '
                                                        '27.0, 27.5, 28.0, 28.4, 28.7, 28.9, '
                                                        '29.0, 28.9, 28.7, 28.4, 28.0, 27.5]')
        try:
            self.__conf['temperature']['dynamicDefault'] = ast.literal_eval(in_conf['temperature']['dynamicDefault'])
            if (type(self.__conf['temperature']['dynamicDefault']) is not list
                    or len (self.__conf['temperature']['dynamicDefault']) != 24):
                raise
            # explicitly convert integers to floats
            self.__conf['temperature']['dynamicDefault'] = [ float(x) if type(x) is int else x for x in self.__conf['temperature']['dynamicDefault'] ]
            if len([ x for x in self.__conf['temperature']['dynamicDefault'] if type(x) is not float ]) > 1:
                raise
            # check values against min/max in valid temperature range
            if len([ x for x in self.__conf['temperature']['dynamicDefault']
                     if x < self.__conf['temperature']['validRange'][0]
                     or x > self.__conf['temperature']['validRange'][1] ]) > 1:
                raise
        except:
            raise TypeError(f"Erl2Config: ['temperature']['dynamicDefault'] = [{in_conf['temperature']['dynamicDefault']}] is not a list of 24 floats within the valid range for this sensor")

    # override [] syntax to return dictionaries of parameter values
    def __getitem__(self, key):
        return self.__conf[key]

    # provide a method similar to configparser's section()
    def sections(self):
        return self.__conf.keys()

def main():

    config = Erl2Config()
    #print(os.path.realpath(__file__))
    if config.conf is not None:
        print (f"Erl2Config: Tank Id is [{config.conf['tank']['id']}]")

if __name__ == "__main__": main()

