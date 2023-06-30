#! /usr/bin/python3

from ast import literal_eval
from configparser import ConfigParser
from datetime import datetime as dt
from datetime import timezone as tz
from os import path
from tzlocal import get_localzone

class Erl2Config():

    # hardcoded ERL2 version string
    VERSION = '0.01b (2023-06-30)'

    # top-level categories in the erl2.conf file
    CATEGORIES = [ 'system', 'tank', 'virtualtemp', 'temperature', 'pH', 'heater', 'chiller']

    # use these parameter strings as defaults if they are missing from the erl2.conf file
    def __setDefaults(self):
        self.__default = {}
        for c in self.CATEGORIES:
            self.__default[c] = {}

        self.__default['system']['project'] = 'Default Project'
        self.__default['system']['disableFileLogging'] = 'False'
        self.__default['system']['clockWithSeconds'] = 'False'
        self.__default['system']['clockTwoLines'] = 'False'

        self.__default['tank']['id'] = 'Tank 0'
        self.__default['tank']['location'] = 'Default Location'

        self.__default['virtualtemp']['enabled'] = 'False'

        self.__default['temperature']['displayParameter'] = 'temp.degC'
        self.__default['temperature']['displayDecimals'] = '1'
        self.__default['temperature']['sampleFrequency'] = '5'
        self.__default['temperature']['memoryRetention'] = '86400'
        self.__default['temperature']['loggingFrequency'] = '300'
        self.__default['temperature']['validRange'] = '[10.0, 40.0]'
        self.__default['temperature']['setpointDefault'] = '25.0'
        self.__default['temperature']['offsetDefault'] = '0.1'
        self.__default['temperature']['dynamicDefault'] = ('[27.0, 26.5, 26.0, 25.6, 25.3, 25.1, '
                                                           '25.0, 25.1, 25.3, 25.6, 26.0, 26.5, '
                                                           '27.0, 27.5, 28.0, 28.4, 28.7, 28.9, '
                                                           '29.0, 28.9, 28.7, 28.4, 28.0, 27.5]')

        self.__default['pH']['displayParameter'] = 'pH'
        self.__default['pH']['displayDecimals'] = '2'
        self.__default['pH']['sampleFrequency'] = '300'
        self.__default['pH']['memoryRetention'] = '86400'
        self.__default['pH']['loggingFrequency'] = '300'
        self.__default['pH']['validRange'] = '[6.00, 9.00]'
        self.__default['pH']['setpointDefault'] = '7.80'
        self.__default['pH']['offsetDefault'] = '0.01'
        self.__default['pH']['dynamicDefault'] = ('[8.00, 7.99, 7.98, 7.96, 7.96, 7.95, '
                                                  '7.95, 7.95, 7.96, 7.96, 7.98, 7.99, '
                                                  '8.00, 8.01, 8.03, 8.04, 8.04, 8.05, '
                                                  '8.05, 8.05, 8.04, 8.04, 8.03, 8.01]')

        self.__default['heater']['loggingFrequency'] = '300'
        self.__default['heater']['memoryRetention'] = '86400'

        self.__default['chiller']['loggingFrequency'] = '300'
        self.__default['chiller']['memoryRetention'] = '86400'

    def __init__(self):

        # initialize configuration object that reads in erl2.conf parameters
        in_conf = ConfigParser()

        # initialize internal parameter dictionary
        self.__erl2conf = {}
        for c in self.CATEGORIES:
            self.__erl2conf[c] = {}

            # there's no guarantee the file will mention all the categories
            if c not in in_conf:
                in_conf[c] = {}

        # the python source file that is currently executing
        thisFile = path.realpath(__file__)

        # the directory holding the currently executing source file
        parent = path.dirname(thisFile)

        # look for erl2.conf in its parent directories one by one
        loop = 0
        while (True):

            # found a file named erl2.conf !
            if path.exists(parent + '/erl2.conf'): 
                self.__erl2conf['system']['rootDir'] = parent
                self.__erl2conf['system']['confFile'] = parent + '/erl2.conf'
                #print (f"{self.__class__.__name__}: Debug: found root directory {self.__erl2conf['system']['rootDir']}")
                #print (f"{self.__class__.__name__}: Debug: found configuration file {self.__erl2conf['system']['confFile']}")
                break

            # give up if there are no higher directories to check
            if parent == path.dirname(parent):
                break

            # next time through the loop, look one level higher up
            parent = path.dirname(parent)

            # avoid infinite looping
            loop += 1
            if loop > 100:
                break

        # if we found a configuration file
        if 'confFile' in self.__erl2conf['system']:

            # read and parse the config file
            in_conf.read(self.__erl2conf['system']['confFile'])

        # otherwise we couldn't find a config
        else:
            raise RuntimeError('Cannot find the erl2.conf configuration file')

        # share the version info with the app
        self.__erl2conf['system']['version'] = self.VERSION

        # record the system startup time
        self.__erl2conf['system']['startup'] = dt.now(tz=tz.utc)

        # whatever the OS considers our local timezone to be
        self.__erl2conf['system']['timezone'] = get_localzone()

        # explicitly define a date+time format to ensure reading/writing is consistent
        # (this one cannot be customized in the erl2.conf file)
        self.__erl2conf['system']['dtFormat'] = '%Y-%m-%d %H:%M:%S'

        # special logic for setting the main log and img directories
        if 'logDir' not in in_conf['system']:
            self.__erl2conf['system']['logDir'] = self.__erl2conf['system']['rootDir'] + '/log'
        else:
            self.__erl2conf['system']['logDir'] = in_conf['system']['logDir']
        if 'imgDir' not in in_conf['system']:
            self.__erl2conf['system']['imgDir'] = self.__erl2conf['system']['rootDir'] + '/img'
        else:
            self.__erl2conf['system']['imgDir'] = in_conf['system']['imgDir']

        # we must insist that the parent of the specified log directory already exists, at least
        if not path.isdir(path.dirname(self.__erl2conf['system']['logDir'])):
            raise TypeError(f"{self.__class__.__name__}: ['system']['logDir'] = [{self.__erl2conf['system']['logDir']}] is not a valid directory")

        # and the images directory itself must exist
        if not path.isdir(self.__erl2conf['system']['imgDir']):
            raise TypeError(f"{self.__class__.__name__}: ['system']['imgDir'] = [{self.__erl2conf['system']['imgDir']}] is not a valid directory")

        # here is where we will define default values for key parameters,
        # in case any crucial values are missing from the erl2.conf file.
        # we are also doing some type-checking at the same time.

        # first, define what the default values should be
        self.__setDefaults()

        # system

        if 'project' not in in_conf['system']:
            in_conf['system']['project'] = self.__default['system']['project']
        self.__erl2conf['system']['project'] = in_conf['system']['project']

        for val in ['disableFileLogging', 'clockWithSeconds', 'clockTwoLines']:
            if val not in in_conf['system']:
                in_conf['system'][val] = self.__default['system'][val]
            try:
                self.__erl2conf['system'][val] = in_conf.getboolean('system',val)
            except:
                raise TypeError(f"{self.__class__.__name__}: ['system'][val] = [{in_conf['system'][val]}] is not boolean")

        # tank

        if 'id' not in in_conf['tank']:
            in_conf['tank']['id'] = self.__default['tank']['id']
        self.__erl2conf['tank']['id'] = in_conf['tank']['id']

        if 'location' not in in_conf['tank']:
            in_conf['tank']['location'] = self.__default['tank']['location']
        self.__erl2conf['tank']['location'] = in_conf['tank']['location']

        # whether to use a 'virtual' temperature sensor...

        if 'enabled' not in in_conf['virtualtemp']:
            in_conf['virtualtemp']['enabled'] = self.__default['virtualtemp']['enabled']
        try:
            self.__erl2conf['virtualtemp']['enabled'] = in_conf.getboolean('virtualtemp','enabled')
        except:
            raise TypeError(f"{self.__class__.__name__}: ['virtualtemp']['enabled'] = [{in_conf['virtualtemp']['enabled']}] is not boolean")

        # temperature and pH share a lot of the same parameter logic

        for sensorType in ['temperature', 'pH']:

            if 'displayParameter' not in in_conf[sensorType]:
                in_conf[sensorType]['displayParameter'] = self.__default[sensorType]['displayParameter']
            self.__erl2conf[sensorType]['displayParameter'] = in_conf[sensorType]['displayParameter']

            if 'displayDecimals' not in in_conf[sensorType]:
                in_conf[sensorType]['displayDecimals'] = self.__default[sensorType]['displayDecimals']
            try:
                self.__erl2conf[sensorType]['displayDecimals'] = int(in_conf[sensorType]['displayDecimals'])
                if self.__erl2conf[sensorType]['displayDecimals'] < 0:
                    raise TypeError
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['displayDecimals'] = [{self.__erl2conf[sensorType]['displayDecimals']}] is not a positive integer")

            if 'sampleFrequency' not in in_conf[sensorType]:
                in_conf[sensorType]['sampleFrequency'] = self.__default[sensorType]['sampleFrequency']
            try:
                self.__erl2conf[sensorType]['sampleFrequency'] = int(in_conf[sensorType]['sampleFrequency'])
                if self.__erl2conf[sensorType]['sampleFrequency'] <= 0:
                    raise TypeError
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['sampleFrequency'] = [{self.__erl2conf[sensorType]['sampleFrequency']}] is not a positive integer")

            if 'memoryRetention' not in in_conf[sensorType]:
                in_conf[sensorType]['memoryRetention'] = self.__default[sensorType]['memoryRetention']
            try:
                self.__erl2conf[sensorType]['memoryRetention'] = int(in_conf[sensorType]['memoryRetention'])
                if self.__erl2conf[sensorType]['memoryRetention'] <= 0:
                    raise TypeError
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['memoryRetention'] = [{self.__erl2conf[sensorType]['memoryRetention']}] is not a positive integer")

            if 'loggingFrequency' not in in_conf[sensorType]:
                in_conf[sensorType]['loggingFrequency'] = self.__default[sensorType]['loggingFrequency']
            try:
                self.__erl2conf[sensorType]['loggingFrequency'] = int(in_conf[sensorType]['loggingFrequency'])
                if self.__erl2conf[sensorType]['loggingFrequency'] <= 0:
                    raise TypeError
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['loggingFrequency'] = [{self.__erl2conf[sensorType]['loggingFrequency']}] is not a positive integer")

            if 'validRange' not in in_conf[sensorType]:
                in_conf[sensorType]['validRange'] = self.__default[sensorType]['validRange']
            try:
                # convert a string that looks like a Python list into an actual Python list
                self.__erl2conf[sensorType]['validRange'] = literal_eval(in_conf[sensorType]['validRange'])
                if (type(self.__erl2conf[sensorType]['validRange']) is not list
                        or len (self.__erl2conf[sensorType]['validRange']) != 2):
                    raise
                # explicitly convert integers to floats
                self.__erl2conf[sensorType]['validRange'] = [ float(x) if type(x) is int else x for x in self.__erl2conf[sensorType]['validRange'] ]
                if len([ x for x in self.__erl2conf[sensorType]['validRange'] if type(x) is not float ]) > 1:
                    raise
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['validRange'] = [{in_conf[sensorType]['validRange']}] is not a list of 2 floats")

            if 'setpointDefault' not in in_conf[sensorType]:
                in_conf[sensorType]['setpointDefault'] = self.__default[sensorType]['setpointDefault']
            try:
                self.__erl2conf[sensorType]['setpointDefault'] = float(in_conf[sensorType]['setpointDefault'])
                # check value against min/max in valid temperature range
                if (self.__erl2conf[sensorType]['setpointDefault'] < self.__erl2conf[sensorType]['validRange'][0]
                        or self.__erl2conf[sensorType]['setpointDefault'] > self.__erl2conf[sensorType]['validRange'][1]):
                    raise
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['setpointDefault'] = [{in_conf[sensorType]['setpointDefault']}] is not a float within the valid range for this sensor")

            if 'offsetDefault' not in in_conf[sensorType]:
                in_conf[sensorType]['offsetDefault'] = self.__default[sensorType]['offsetDefault']
            try:
                self.__erl2conf[sensorType]['offsetDefault'] = float(in_conf[sensorType]['offsetDefault'])
                if self.__erl2conf[sensorType]['offsetDefault'] <= 0.:
                    raise
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['offsetDefault'] = [{in_conf[sensorType]['offsetDefault']}] is not a positive float")

            if 'dynamicDefault' not in in_conf[sensorType]:
                in_conf[sensorType]['dynamicDefault'] = self.__default[sensorType]['dynamicDefault']
            try:
                self.__erl2conf[sensorType]['dynamicDefault'] = literal_eval(in_conf[sensorType]['dynamicDefault'])
                if (type(self.__erl2conf[sensorType]['dynamicDefault']) is not list
                        or len (self.__erl2conf[sensorType]['dynamicDefault']) != 24):
                    raise
                # explicitly convert integers to floats
                self.__erl2conf[sensorType]['dynamicDefault'] = [ float(x) if type(x) is int else x for x in self.__erl2conf[sensorType]['dynamicDefault'] ]
                if len([ x for x in self.__erl2conf[sensorType]['dynamicDefault'] if type(x) is not float ]) > 1:
                    raise
                # check values against min/max in valid temperature range
                if len([ x for x in self.__erl2conf[sensorType]['dynamicDefault']
                         if x < self.__erl2conf[sensorType]['validRange'][0]
                         or x > self.__erl2conf[sensorType]['validRange'][1] ]) > 1:
                    raise
            except:
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['dynamicDefault'] = [{in_conf[sensorType]['dynamicDefault']}] is not a list of 24 floats within the valid range for this sensor")

        # if using the virtual temperature sensor, duplicate its settings from temperature

        if self.__erl2conf['virtualtemp']['enabled']:
            self.__erl2conf['virtualtemp'] = {**self.__erl2conf['virtualtemp'], **self.__erl2conf['temperature']}

        # heater and chiller share a lot of the same parameter logic

        for controlType in ['heater', 'chiller']:
            if 'loggingFrequency' not in in_conf[controlType]:
                in_conf[controlType]['loggingFrequency'] = self.__default[controlType]['loggingFrequency']
            try:
                self.__erl2conf[controlType]['loggingFrequency'] = int(in_conf[controlType]['loggingFrequency'])
                if self.__erl2conf[controlType]['loggingFrequency'] <= 0:
                    raise TypeError
            except:
                raise TypeError(f"{self.__class__.__name__}: [{controlType}]['loggingFrequency'] = [{self.__erl2conf[controlType]['loggingFrequency']}] is not a positive integer")

            if 'memoryRetention' not in in_conf[controlType]:
                in_conf[controlType]['memoryRetention'] = self.__default[controlType]['memoryRetention']
            try:
                self.__erl2conf[controlType]['memoryRetention'] = int(in_conf[controlType]['memoryRetention'])
                if self.__erl2conf[controlType]['memoryRetention'] <= 0:
                    raise TypeError
            except:
                raise TypeError(f"{self.__class__.__name__}: [{controlType}]['memoryRetention'] = [{self.__erl2conf[controlType]['memoryRetention']}] is not a positive integer")

    # override [] syntax to return dictionaries of parameter values
    def __getitem__(self, key):
        return self.__erl2conf[key]

    # provide a method similar to configparser's section()
    def sections(self):
        return self.__erl2conf.keys()

