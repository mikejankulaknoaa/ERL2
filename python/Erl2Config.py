from ast import literal_eval
from configparser import ConfigParser
from datetime import datetime as dt
from datetime import timezone as tz
from os import path
from sys import platform
from tzlocal import get_localzone

class Erl2Config():

    # hardcoded ERL2 version string
    VERSION = '0.42b (2024-03-29b)'

    # top-level categories in the erl2.conf file
    CATEGORIES = [ 'system', 'device', 'network', 'virtualtemp', 'temperature', 'pH', 'DO', 'generic', 'heater', 'chiller', 'mfc.air', 'mfc.co2', 'mfc.n2']

    # valid baud rates (borrowed from the pyrolib code)
    BAUDS = [ 1200,  2400,   4800,   9600,  14400,  19200,  28800,  38400,  38400,
             56000, 57600, 115200, 128000, 153600, 230400, 256000, 460800, 921600]

    # use these parameter strings as defaults if they are missing from the erl2.conf file
    def __setDefaults(self):
        self.__default = {}
        for c in self.CATEGORIES:
            self.__default[c] = {}

        self.__default['system']['clockWithSeconds'] = 'False'
        self.__default['system']['clockTwoLines'] = 'False'
        self.__default['system']['loggingFrequency'] = '300'
        self.__default['system']['memoryRetention'] = '86400'

        self.__default['device']['type'] = 'tank'
        self.__default['device']['id'] = 'Tank 0'

        self.__default['network']['controllerIP'] = 'None'
        self.__default['network']['enabled'] = 'False'
        self.__default['network']['ipNetworkStub'] = '192.168.2.'
        self.__default['network']['ipRange'] = '[2, 63]'
        self.__default['network']['updateFrequency'] = '5'
        self.__default['network']['hardcoding'] = 'None'

        self.__default['virtualtemp']['enabled'] = 'False'

        self.__default['temperature']['stackLevel'] = '0'
        self.__default['temperature']['inputChannel'] = '1'
        self.__default['temperature']['channelType'] = 'milliAmps'
        self.__default['temperature']['parameterName'] = 'temp.degC'
        self.__default['temperature']['hardwareRange'] = '[0.0, 100.0]'

        self.__default['temperature']['displayParameter'] = 'temp.degC'
        self.__default['temperature']['displayDecimals'] = '1'
        self.__default['temperature']['sampleFrequency'] = '5'
        self.__default['temperature']['loggingFrequency'] = '300'
        self.__default['temperature']['offsetParameter'] = 'temp.degC'
        self.__default['temperature']['offsetDefault'] = '0.0'
        self.__default['temperature']['validRange'] = '[10.0, 40.0]'

        self.__default['temperature']['hysteresisDefault'] = '0.1'
        self.__default['temperature']['setpointDefault'] = '25.0'
        self.__default['temperature']['dynamicDefault'] = ('[27.0, 26.5, 26.0, 25.6, 25.3, 25.1, '
                                                            '25.0, 25.1, 25.3, 25.6, 26.0, 26.5, '
                                                            '27.0, 27.5, 28.0, 28.4, 28.7, 28.9, '
                                                            '29.0, 28.9, 28.7, 28.4, 28.0, 27.5]')

        self.__default['pH']['serialPort'] = '/dev/ttyAMA1'
        self.__default['pH']['baudRate'] = '19200'

        self.__default['pH']['displayParameter'] = 'pH'
        self.__default['pH']['displayDecimals'] = '2'
        self.__default['pH']['sampleFrequency'] = '60'
        self.__default['pH']['loggingFrequency'] = '300'
        self.__default['pH']['offsetParameter'] = 'pH'
        self.__default['pH']['offsetDefault'] = '0.00'
        self.__default['pH']['validRange'] = '[6.00, 9.00]'

        self.__default['pH']['setpointDefault'] = '7.80'
        self.__default['pH']['dynamicDefault'] = ('[8.00, 7.99, 7.98, 7.96, 7.96, 7.95, '
                                                   '7.95, 7.95, 7.96, 7.96, 7.98, 7.99, '
                                                   '8.00, 8.01, 8.03, 8.04, 8.04, 8.05, '
                                                   '8.05, 8.05, 8.04, 8.04, 8.03, 8.01]')

        self.__default['pH']['mfc.air.Kp'] = '10000.0'
        self.__default['pH']['mfc.air.Ki'] = '1000.0'
        self.__default['pH']['mfc.air.Kd'] = '0.0'
        self.__default['pH']['mfc.co2.Kp'] = '-40.0'
        self.__default['pH']['mfc.co2.Ki'] = '-4.0'
        self.__default['pH']['mfc.co2.Kd'] = '0.0'

        self.__default['DO']['serialPort'] = '/dev/ttyAMA2'
        self.__default['DO']['baudRate'] = '19200'

        self.__default['DO']['displayParameter'] = 'uM'
        self.__default['DO']['displayDecimals'] = '0'
        self.__default['DO']['sampleFrequency'] = '60'
        self.__default['DO']['loggingFrequency'] = '300'
        self.__default['DO']['offsetParameter'] = 'uM'
        self.__default['DO']['offsetDefault'] = '0.'
        self.__default['DO']['validRange'] = '[100., 700.]'

        self.__default['DO']['setpointDefault'] = '300.'
        self.__default['DO']['dynamicDefault'] = ('[300., 294., 288., 282., 278., 276., '
                                                   '275., 276., 278., 282., 288., 294., '
                                                   '300., 306., 313., 318., 322., 324., '
                                                   '325., 324., 322., 318., 313., 306.]')

        self.__default['DO']['mfc.air.Kp'] = '10000.0'
        self.__default['DO']['mfc.air.Ki'] = '1000.0'
        self.__default['DO']['mfc.air.Kd'] = '0.0'
        self.__default['DO']['mfc.n2.Kp'] = '-10000.0'
        self.__default['DO']['mfc.n2.Ki'] = '-1000.0'
        self.__default['DO']['mfc.n2.Kd'] = '0.0'

        self.__default['generic']['displayParameter'] = 'generic'
        self.__default['generic']['displayDecimals'] = '3'
        self.__default['generic']['sampleFrequency'] = '5'
        self.__default['generic']['loggingFrequency'] = '300'
        self.__default['generic']['offsetParameter'] = 'generic'
        self.__default['generic']['offsetDefault'] = '0.000'
        self.__default['generic']['validRange'] = '[-5.000, 5.000]'

        self.__default['generic']['setpointDefault'] = '0.500'
        self.__default['generic']['dynamicDefault'] = ('[0.500, 0.371, 0.250, 0.146, 0.067, 0.017, '
                                                        '0.000, 0.017, 0.067, 0.146, 0.250, 0.371, '
                                                        '0.500, 0.629, 0.750, 0.854, 0.933, 0.983, '
                                                        '1.000, 0.983, 0.933, 0.854, 0.750, 0.629]')

        self.__default['heater']['gpioChannel'] = '23'
        self.__default['heater']['loggingFrequency'] = '300'

        self.__default['chiller']['stackLevel'] = '0'
        self.__default['chiller']['outputPwmChannel'] = '1'
        self.__default['chiller']['loggingFrequency'] = '300'

        self.__default['mfc.air']['stackLevel'] = '0'
        self.__default['mfc.air']['inputChannel'] = '2'
        self.__default['mfc.air']['channelType'] = 'volts'
        self.__default['mfc.air']['parameterName'] = 'flow.mLperMin'
        self.__default['mfc.air']['hardwareRange'] = '[0., 10000.]'
        self.__default['mfc.air']['displayParameter'] = 'flow.mLperMin'
        self.__default['mfc.air']['displayDecimals'] = '0'
        self.__default['mfc.air']['sampleFrequency'] = '5'
        self.__default['mfc.air']['loggingFrequency'] = '300'
        self.__default['mfc.air']['offsetParameter'] = 'flow.mLperMin'
        self.__default['mfc.air']['offsetDefault'] = '0.'
        self.__default['mfc.air']['validRange'] = '[0., 5000.]'
        self.__default['mfc.air']['outputChannel'] = '1'
        self.__default['mfc.air']['flowRateRange'] = '[0., 5000.]'

        self.__default['mfc.co2']['stackLevel'] = '0'
        self.__default['mfc.co2']['inputChannel'] = '3'
        self.__default['mfc.co2']['channelType'] = 'volts'
        self.__default['mfc.co2']['parameterName'] = 'flow.mLperMin'
        self.__default['mfc.co2']['hardwareRange'] = '[0.0, 40.0]'
        self.__default['mfc.co2']['displayParameter'] = 'flow.mLperMin'
        self.__default['mfc.co2']['displayDecimals'] = '1'
        self.__default['mfc.co2']['sampleFrequency'] = '5'
        self.__default['mfc.co2']['loggingFrequency'] = '300'
        self.__default['mfc.co2']['offsetParameter'] = 'flow.mLperMin'
        self.__default['mfc.co2']['offsetDefault'] = '0.0'
        self.__default['mfc.co2']['validRange'] = '[0.0, 20.0]'
        self.__default['mfc.co2']['outputChannel'] = '2'
        self.__default['mfc.co2']['flowRateRange'] = '[0.0, 20.0]'

        self.__default['mfc.n2']['stackLevel'] = '0'
        self.__default['mfc.n2']['inputChannel'] = '4'
        self.__default['mfc.n2']['channelType'] = 'volts'
        self.__default['mfc.n2']['parameterName'] = 'flow.mLperMin'
        self.__default['mfc.n2']['hardwareRange'] = '[0., 10000.]'
        self.__default['mfc.n2']['displayParameter'] = 'flow.mLperMin'
        self.__default['mfc.n2']['displayDecimals'] = '0'
        self.__default['mfc.n2']['sampleFrequency'] = '5'
        self.__default['mfc.n2']['loggingFrequency'] = '300'
        self.__default['mfc.n2']['offsetParameter'] = 'flow.mLperMin'
        self.__default['mfc.n2']['offsetDefault'] = '0.'
        self.__default['mfc.n2']['validRange'] = '[0., 5000.]'
        self.__default['mfc.n2']['outputChannel'] = '3'
        self.__default['mfc.n2']['flowRateRange'] = '[0., 5000.]'

    def __init__(self):

        # initialize configuration object that reads in erl2.conf parameters
        self.in_conf = ConfigParser()

        # initialize internal parameter dictionary
        self.__erl2conf = {}
        for c in self.CATEGORIES:
            self.__erl2conf[c] = {}

            # there's no guarantee the file will mention all the categories
            if c not in self.in_conf:
                self.in_conf[c] = {}

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
            self.in_conf.read(self.__erl2conf['system']['confFile'])

        # otherwise we couldn't find a config
        else:
            raise RuntimeError('Cannot find the erl2.conf configuration file')

        # what OS are we running?
        self.__erl2conf['system']['platform'] = platform

        # share the version info with the app
        self.__erl2conf['system']['version'] = self.VERSION

        # record the system startup time
        self.__erl2conf['system']['startup'] = dt.now(tz=tz.utc)

        # whatever the OS considers our local timezone to be
        self.__erl2conf['system']['timezone'] = get_localzone()

        # whether app is in shutdown or not
        self.__erl2conf['system']['shutdown'] = False

        # explicitly define a date+time format to ensure reading/writing is consistent
        # (these cannot be customized in the erl2.conf file)
        self.__erl2conf['system']['dtFormat'] = '%Y-%m-%d %H:%M:%S'
        self.__erl2conf['system']['dtRegexp'] = r'^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'

        # special logic for setting the main ERL2 directories
        for d in ['img','lock','log']:
            dname = d + 'Dir'
            if dname not in self.in_conf['system']:
                self.__erl2conf['system'][dname] = self.__erl2conf['system']['rootDir'] + '/' + d
            else:
                self.__erl2conf['system'][dname] = self.in_conf['system'][dname]

            # we must insist that the parent of the specified directory already exists, at least
            if not path.isdir(path.dirname(self.__erl2conf['system'][dname])):
                raise TypeError(f"{self.__class__.__name__}: ['system']['{dname}'] = [{self.__erl2conf['system'][dname]}] is not a valid directory")

        # here is where we will define default values for key parameters,
        # in case any crucial values are missing from the erl2.conf file.
        # we are also doing some type-checking at the same time.

        # first, define what the default values should be
        self.__setDefaults()

        # system
        self.validate(bool, 'system', 'clockWithSeconds')
        self.validate(bool, 'system', 'clockTwoLines')
        self.validate(int,  'system', 'loggingFrequency', min=1)
        self.validate(int,  'system', 'memoryRetention',  min=300)

        # device
        self.validate(str, 'device', 'type')
        if self.__erl2conf['device']['type'] not in ['tank', 'controller']:
            raise TypeError(f"{self.__class__.__name__}: ['device']['type'] = [{self.__erl2conf['device']['type']}] must be 'tank' or 'controller'")
        self.validate(str, 'device', 'id')

        # network
        self.validate(str,  'network', 'controllerIP')
        self.validate(bool, 'network', 'enabled')
        self.validate(str,  'network', 'ipNetworkStub')
        self.validate(int,  'network', 'updateFrequency', min=1)

        self.validateList(str, 'network', 'hardcoding')

        # ipRange has some extra logic (non-decreasing order)
        self.validateList(int, 'network', 'ipRange', 2)
        if (self.__erl2conf['network']['ipRange'] is not None
            and self.__erl2conf['network']['ipRange'][0] > self.__erl2conf['network']['ipRange'][1]):
            raise TypeError(f"{self.__class__.__name__}: ['network']['ipRange'] = {self.__erl2conf['network']['ipRange']} must specified in increasing order")

        # whether to use a 'virtual' temperature sensor...
        self.validate(bool, 'virtualtemp', 'enabled')

        # temperature is the only category that has hysteresis
        self.validate(float, 'temperature', 'hysteresisDefault', min=0.)

        # any Input 4-20mA or 0-10V sensor (temperature, MFCs) has these parameters
        for sensorType in ['temperature', 'mfc.air', 'mfc.co2', 'mfc.n2']:
            self.validate(int, sensorType, 'stackLevel',   min=0, max=7)
            self.validate(int, sensorType, 'inputChannel', min=1, max=4)
            self.validate(str, sensorType, 'parameterName')

            # what type of input channel does the sensor use? volts or milliAmps
            self.validate(str,  sensorType, 'channelType')
            if self.__erl2conf[sensorType]['channelType'] not in ['volts', 'milliAmps']:
                raise TypeError(f"{self.__class__.__name__}: [sensorType]['channelType'] = [{self.__erl2conf[sensorType]['channelType']}] must be 'volts' or 'milliAmps'")

            # hardwareRange has some extra logic (non-decreasing order)
            self.validateList(float, sensorType, 'hardwareRange', 2)
            if (self.__erl2conf[sensorType]['hardwareRange'] is not None
                and self.__erl2conf[sensorType]['hardwareRange'][0] > self.__erl2conf[sensorType]['hardwareRange'][1]):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['hardwareRange'] = {self.__erl2conf[sensorType]['hardwareRange']} must specified in increasing order")

        # pH and DO comms parameters (serial port and baud rate)
        for sensorType in ['pH', 'DO']:
            self.validate(str, sensorType, 'serialPort')
            self.validate(int, sensorType, 'baudRate')

            if (self.__erl2conf[sensorType]['serialPort'] is not None
                and not path.exists(self.__erl2conf[sensorType]['serialPort'])):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['serialPort'] = [{self.__erl2conf[sensorType]['serialPort']}] does not exist on this system")

            if (self.__erl2conf[sensorType]['baudRate'] is not None
                and self.__erl2conf[sensorType]['baudRate'] not in self.BAUDS):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['baudRate'] = [{self.__erl2conf[sensorType]['baudRate']}] is not a valid baud rate.\nValid baud rates are [{self.BAUDS}].")

        # temperature, pH, DO and the MFCs share a lot of the same parameter logic
        for sensorType in ['temperature', 'pH', 'DO', 'mfc.air', 'mfc.co2', 'mfc.n2', 'generic']:

            # some sensors have hardwareRange as well as validRange
            if 'hardwareRange' in self.__erl2conf[sensorType]:
                minVal = self.__erl2conf[sensorType]['hardwareRange'][0]
                maxVal = self.__erl2conf[sensorType]['hardwareRange'][1]
            else:
                minVal = None
                maxVal = None

            # validRange has some extra logic (non-decreasing order)
            self.validateList(float, sensorType, 'validRange', 2, min=minVal, max=maxVal)
            if (self.__erl2conf[sensorType]['validRange'] is not None
                and self.__erl2conf[sensorType]['validRange'][0] > self.__erl2conf[sensorType]['validRange'][1]):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['validRange'] = {self.__erl2conf[sensorType]['validRange']} must specified in increasing order")

            self.validate(str,   sensorType, 'displayParameter')
            self.validate(int,   sensorType, 'displayDecimals',  min=0)
            self.validate(int,   sensorType, 'sampleFrequency',  min=1)
            self.validate(int,   sensorType, 'loggingFrequency', min=1)
            self.validate(str,   sensorType, 'offsetParameter')
            self.validate(float, sensorType, 'offsetDefault')

        # temperature, pH, and DO share the setpoint-related logic
        for sensorType in ['temperature', 'pH', 'DO', 'generic']:

            # these are required to fall within the validRange for the sensor
            self.validate    (float, sensorType, 'setpointDefault',    min=self.__erl2conf[sensorType]['validRange'][0], max=self.__erl2conf[sensorType]['validRange'][1])
            self.validateList(float, sensorType, 'dynamicDefault', 24, min=self.__erl2conf[sensorType]['validRange'][0], max=self.__erl2conf[sensorType]['validRange'][1])

        # the pH and DO subsystems require PID parameter values for their controls
        for sys in 'pH', 'DO':
            for param in 'Kp', 'Ki', 'Kd':
                for gas in 'air', 'co2', 'n2':
                    # only some combinations are valid
                    if ((gas == 'air') or (gas == 'co2' and sys == 'pH') or (gas == 'n2' and sys == 'DO')):
                        self.validate(float, sys, f"mfc.{gas}.{param}")

        # the virtual temperature sensor might be required even if not explicitly enabled
        self.__erl2conf['virtualtemp'] = {**self.__erl2conf['virtualtemp'], **self.__erl2conf['temperature']}

        # individual heater/chiller parameters
        self.validate(int, 'heater',  'gpioChannel',      min=1, max=27)
        self.validate(int, 'chiller', 'stackLevel',       min=0, max=7)
        self.validate(int, 'chiller', 'outputPwmChannel', min=1, max=4)

        # controls (heater, chiller, mfc.air, mfc.co2, mfc.n2) share some parameter logic
        for controlType in ['heater', 'chiller', 'mfc.air', 'mfc.co2', 'mfc.n2']:
            self.validate(int, controlType, 'loggingFrequency', min=1)

        # MFCs (mfc.air, mfc.co2, mfc.n2) share some parameter logic
        for controlType in ['mfc.air', 'mfc.co2', 'mfc.n2']:

            # flowRateRange has some extra logic (non-decreasing order)
            self.validateList(float, controlType, 'flowRateRange', 2, min=self.__erl2conf[controlType]['hardwareRange'][0], max=self.__erl2conf[controlType]['hardwareRange'][1])
            if (self.__erl2conf[controlType]['flowRateRange'] is not None
                and self.__erl2conf[controlType]['flowRateRange'][0] > self.__erl2conf[controlType]['flowRateRange'][1]):
                raise TypeError(f"{self.__class__.__name__}: [{controlType}]['flowRateRange'] = {self.__erl2conf[controlType]['flowRateRange']} must specified in increasing order")

            self.validate(int, controlType, 'outputChannel', min=1, max=4)

    def validate(self, cl, cat, param, min=None, max=None):

        #print (f"{self.__class__.__name__}: Debug: validate({cl.__name__},{cat},{param},{min},{max})")

        # pull value from system defaults if missing from the erl2.conf file
        if param not in self.in_conf[cat]:
            self.in_conf[cat][param] = self.__default[cat][param]

        # special case: None
        if self.in_conf[cat][param] == 'None':
            self.__erl2conf[cat][param] = None
            return

        # attempt the conversion to the requested class
        try:
            # special handling for booleans
            if cl == bool:
                self.__erl2conf[cat][param] = self.in_conf.getboolean(cat,param)
            else:
                self.__erl2conf[cat][param] = cl(self.in_conf[cat][param])

            # if bounds are specified, check them
            if (   (min is not None and self.__erl2conf[cat][param] < min)
                or (max is not None and self.__erl2conf[cat][param] > max)):
                raise TypeError

        except:
            # prettify the type name if possible
            if cl is str:
                tp = 'a string'
            elif cl is int:
                tp = 'an integer'
            elif cl is bool:
                tp = 'a boolean'
            elif cl is float:
                tp = 'a float'
            else:
                tp = f"of class [{cl.__name__}]"

            # add optional error info about min/max requirements
            msg = ''
            if min is not None and max is not None:
                msg = f" between [{min}] and [{max}]"
            elif min is not None:
                msg = f" greater than [{min}]"
            elif max is not None:
                msg = f" less than [{max}]"

            raise TypeError(f"{self.__class__.__name__}: [{cat}][{param}] = [{self.in_conf[cat][param]}] is not {tp}{msg}") #from None


    def validateList(self, cl, cat, param, cnt=None, min=None, max=None):

        #print (f"{self.__class__.__name__}: Debug: validateList({cl.__name__},{cat},{param},{cnt},{min},{max})")

        # pull value from system defaults if missing from the erl2.conf file
        if param not in self.in_conf[cat]:
            self.in_conf[cat][param] = self.__default[cat][param]

        # special case: None
        if self.in_conf[cat][param] == 'None':
            self.__erl2conf[cat][param] = None
            return

        # attempt the conversion to the requested class
        try:
            # convert a string that looks like a Python list into an actual Python list
            self.__erl2conf[cat][param] = literal_eval(self.in_conf[cat][param])

            # is it a list?
            if type(self.__erl2conf[cat][param]) is not list:
                raise

            # if length is specified, is it the expected length?
            if (    cnt is not None
                and len(self.__erl2conf[cat][param]) != cnt):
                raise

            # explicitly convert values to requested class
            self.__erl2conf[cat][param] = [ cl(x) if type(x) is not cl else x for x in self.__erl2conf[cat][param] ]
            if len([ x for x in self.__erl2conf[cat][param] if type(x) is not cl ]) > 0:
                raise

            # if bounds are specified, check them
            if (   (min is not None and len([ x for x in self.__erl2conf[cat][param] if x < min ]) > 0)
                or (max is not None and len([ x for x in self.__erl2conf[cat][param] if x > max ]) > 0)):
                raise TypeError

        except:
            # prettify the type name if possible
            if cl is str:
                tp = 'strings'
            elif cl is int:
                tp = 'integers'
            elif cl is bool:
                tp = 'booleans'
            elif cl is float:
                tp = 'floats'
            else:
                tp = f"instances of class [{cl.__name__}]"

            # add optional error info about min/max requirements
            msg = ''
            if min is not None and max is not None:
                msg = f" between [{min}] and [{max}]"
            elif min is not None:
                msg = f" greater than [{min}]"
            elif max is not None:
                msg = f" less than [{max}]"

            raise TypeError(f"{self.__class__.__name__}: [{cat}][{param}] = {self.in_conf[cat][param]} is not a list of {tp}{msg}") from None

    # override [] syntax to return dictionaries of parameter values
    def __getitem__(self, key):
        return self.__erl2conf[key]

    # provide a method similar to configparser's section()
    def sections(self):
        return self.__erl2conf.keys()

def main():

    config = Erl2Config()
    print ("Erl2Config module (no GUI)")

if __name__ == "__main__": main()

