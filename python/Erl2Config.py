from ast import literal_eval
from configparser import ConfigParser
from datetime import datetime as dt
from datetime import timezone as tz
from os import makedirs,path
from sys import platform
from tzlocal import get_localzone

# hardcoded ERL2 version string
VERSION = '0.086 (2024-09-30b)'

# top-level categories in the erl2.conf file
CATEGORIES = ['system', 'device', 'network', 'virtualtemp',
              'temperature', 'pH', 'DO', 'generic', 'heater',
              'chiller', 'mfc.air', 'mfc.co2', 'mfc.n2', 'voltage']

# valid baud rates (borrowed from the pyrolib code)
BAUDS = [ 1200,  2400,   4800,   9600,  14400,  19200,  28800,  38400,  38400,
         56000, 57600, 115200, 128000, 153600, 230400, 256000, 460800, 921600]

# valid modes
MODES = ['manual', 'auto_static', 'auto_dynamic']

# main directories that must be created if they don't already exist
MAINDIRS = ['img', 'lock', 'log']

class Erl2Config():

    def __init__(self,
                 configType = 'erl2',
                 version = VERSION,
                 categories = CATEGORIES,
                 maindirs = MAINDIRS,
                 thisFile = __file__
                 ):

        self.configType = configType
        self.version = version
        self.categories = categories
        self.maindirs = maindirs

        # initialize configuration object that reads in .conf parameters
        self.in_conf = ConfigParser()

        # initialize internal parameter dictionaries
        self.mainConfig = {}
        self.default = {}

        for c in self.categories:
            self.mainConfig[c] = {}
            self.default[c] = {}

            # there's no guarantee the file will mention all the categories
            if c not in self.in_conf:
                self.in_conf[c] = {}

        # the python source file that is currently executing
        thisFile = path.realpath(thisFile)

        # the directory holding the currently executing source file
        parent = path.dirname(thisFile)

        # look for .conf file in its parent directories one by one
        loop = 0
        while (True):

            # found a file named {configType}.conf !
            if path.exists(parent + f"/{self.configType}.conf"):
                self.mainConfig['system']['rootDir'] = parent
                self.mainConfig['system']['confFile'] = parent + f"/{self.configType}.conf"
                #print (f"{self.__class__.__name__}: Debug: found root directory {self.mainConfig['system']['rootDir']}")
                #print (f"{self.__class__.__name__}: Debug: found configuration file {self.mainConfig['system']['confFile']}")
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
        if 'confFile' in self.mainConfig['system']:

            # read and parse the config file
            self.in_conf.read(self.mainConfig['system']['confFile'])

        # otherwise we couldn't find a config
        else:
            raise RuntimeError(f"Cannot find the {self.configType}.conf configuration file")

        # what OS are we running?
        #print (f"{self.__class__.__name__}: Debug: found platform is [{platform}]")
        self.mainConfig['system']['platform'] = platform

        # share the version info with the app
        self.mainConfig['system']['version'] = self.version

        # record the system startup time
        self.mainConfig['system']['startup'] = dt.now(tz=tz.utc)

        # whatever the OS considers our local timezone to be
        self.mainConfig['system']['timezone'] = get_localzone()

        # whether app is in shutdown or not
        self.mainConfig['system']['shutdown'] = False

        # explicitly define a date+time format to ensure reading/writing is consistent
        # (these cannot be customized in the .conf file)
        self.mainConfig['system']['dtFormat'] = '%Y-%m-%d %H:%M:%S'
        self.mainConfig['system']['dtRegexp'] = r'^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'

        # special logic for setting up the main directories
        for d in self.maindirs:
            dname = d + 'Dir'
            if dname not in self.in_conf['system']:
                self.mainConfig['system'][dname] = self.mainConfig['system']['rootDir'] + '/' + d
            else:
                self.mainConfig['system'][dname] = self.in_conf['system'][dname]

            # we must insist that the parent of the specified directory already exists, at least
            if not path.isdir(self.mainConfig['system'][dname]):
                makedirs(self.mainConfig['system'][dname], exist_ok=True)

                # one last check to make sure the directory creation worked
                if not path.isdir(self.mainConfig['system'][dname]):
                    raise TypeError(f"{self.__class__.__name__}: ['system']['{dname}'] = " +
                                    f"[{self.mainConfig['system'][dname]}] is not a valid directory")

        # here is where we will define default values for key parameters,
        # in case any crucial values are missing from the .conf file.
        # we are also doing some type-checking at the same time.

        # first, define what the default values should be
        self.setDefaults()

        # then, read .conf file values, validate, and override defaults
        self.validateConfig()

    # use these parameter strings as defaults if they are missing from the erl2.conf file
    def setDefaults(self):

        self.default['system']['hideClockSeconds'] = 'False'
        self.default['system']['clockTwoLines'] = 'False'
        self.default['system']['loggingFrequency'] = '300'
        self.default['system']['memoryRetention'] = '86400'

        self.default['device']['type'] = 'tank'
        self.default['device']['id'] = 'Tank 0'

        self.default['network']['enabled'] = 'False'
        self.default['network']['controllerIP'] = 'None'
        self.default['network']['ipNetworkStub'] = 'None'
        self.default['network']['ipRange'] = '[2, 254]'
        self.default['network']['hardcoding'] = 'None'
        self.default['network']['updateFrequency'] = '5'
        self.default['network']['lapseTime'] = '60'

        self.default['virtualtemp']['enabled'] = 'False'

        self.default['temperature']['serialPort'] = '/dev/ttyAMA5'
        self.default['temperature']['baudRate'] = '9600'
        self.default['temperature']['stackLevel'] = '0'
        self.default['temperature']['inputChannel'] = '1'
        self.default['temperature']['channelType'] = 'milliAmps'
        self.default['temperature']['parameterName'] = 'temp.degC'
        self.default['temperature']['hardwareRange'] = '[0.0, 100.0]'

        self.default['temperature']['displayParameter'] = 'temp.degC'
        self.default['temperature']['displayDecimals'] = '1'
        self.default['temperature']['sampleFrequency'] = '5'
        self.default['temperature']['loggingFrequency'] = '300'
        self.default['temperature']['offsetParameter'] = 'temp.degC'
        self.default['temperature']['offsetDefault'] = '0.000'
        self.default['temperature']['validRange'] = '[10.0, 40.0]'

        self.default['temperature']['modeNameDefault'] = 'manual'
        self.default['temperature']['hysteresisDefault'] = '0.100'
        self.default['temperature']['setpointDefault'] = '25.0'
        self.default['temperature']['dynamicDefault'] = ('[27.0, 26.5, 26.0, 25.6, 25.3, 25.1, '
                                                            '25.0, 25.1, 25.3, 25.6, 26.0, 26.5, '
                                                            '27.0, 27.5, 28.0, 28.4, 28.7, 28.9, '
                                                            '29.0, 28.9, 28.7, 28.4, 28.0, 27.5]')

        self.default['voltage']['parameterName'] = 'voltage'
        self.default['voltage']['hardwareRange'] = '[0.0, 36.0]'
        self.default['voltage']['displayParameter'] = 'voltage'
        self.default['voltage']['displayDecimals'] = '5'
        self.default['voltage']['sampleFrequency'] = '5'
        self.default['voltage']['loggingFrequency'] = '300'
        self.default['voltage']['offsetParameter'] = 'None'
        self.default['voltage']['offsetDefault'] = '0.00000'
        self.default['voltage']['validRange'] = '[0.0, 36.0]'

        self.default['pH']['serialPort'] = '/dev/ttyAMA2'
        self.default['pH']['baudRate'] = '19200'

        self.default['pH']['displayParameter'] = 'pH'
        self.default['pH']['displayDecimals'] = '2'
        self.default['pH']['sampleFrequency'] = '60'
        self.default['pH']['loggingFrequency'] = '300'
        self.default['pH']['offsetParameter'] = 'pH'
        self.default['pH']['offsetDefault'] = '0.0000'
        self.default['pH']['validRange'] = '[6.00, 9.00]'

        self.default['pH']['modeNameDefault'] = 'manual'
        self.default['pH']['setpointDefault'] = '7.80'
        self.default['pH']['dynamicDefault'] = ('[8.00, 7.99, 7.98, 7.96, 7.96, 7.95, '
                                                   '7.95, 7.95, 7.96, 7.96, 7.98, 7.99, '
                                                   '8.00, 8.01, 8.03, 8.04, 8.04, 8.05, '
                                                   '8.05, 8.05, 8.04, 8.04, 8.03, 8.01]')

        self.default['pH']['mfc.air.Kp'] = '10000.0'
        self.default['pH']['mfc.air.Ki'] = '1000.0'
        self.default['pH']['mfc.air.Kd'] = '0.0'
        self.default['pH']['mfc.co2.Kp'] = '-40.0'
        self.default['pH']['mfc.co2.Ki'] = '-4.0'
        self.default['pH']['mfc.co2.Kd'] = '0.0'

        self.default['DO']['serialPort'] = '/dev/ttyAMA4'
        self.default['DO']['baudRate'] = '19200'

        self.default['DO']['displayParameter'] = 'uM'
        self.default['DO']['displayDecimals'] = '0'
        self.default['DO']['sampleFrequency'] = '60'
        self.default['DO']['loggingFrequency'] = '300'
        self.default['DO']['offsetParameter'] = 'uM'
        self.default['DO']['offsetDefault'] = '0.00'
        self.default['DO']['validRange'] = '[100., 400.]'

        self.default['DO']['modeNameDefault'] = 'manual'
        self.default['DO']['setpointDefault'] = '220.'
        self.default['DO']['dynamicDefault'] = ('[220., 216., 213., 209., 207., 206., '
                                                   '205., 206., 207., 209., 213., 216., '
                                                   '220., 224., 228., 231., 233., 234., '
                                                   '235., 234., 233., 231., 228., 224.]')

        self.default['DO']['mfc.air.Kp'] = '10000.0'
        self.default['DO']['mfc.air.Ki'] = '1000.0'
        self.default['DO']['mfc.air.Kd'] = '0.0'
        self.default['DO']['mfc.n2.Kp'] = '-10000.0'
        self.default['DO']['mfc.n2.Ki'] = '-1000.0'
        self.default['DO']['mfc.n2.Kd'] = '0.0'

        self.default['generic']['displayParameter'] = 'generic'
        self.default['generic']['displayDecimals'] = '3'
        self.default['generic']['sampleFrequency'] = '5'
        self.default['generic']['loggingFrequency'] = '300'
        self.default['generic']['offsetParameter'] = 'generic'
        self.default['generic']['offsetDefault'] = '0.00000'
        self.default['generic']['validRange'] = '[-5.000, 5.000]'

        self.default['generic']['modeNameDefault'] = 'manual'
        self.default['generic']['setpointDefault'] = '0.500'
        self.default['generic']['dynamicDefault'] = ('[0.500, 0.371, 0.250, 0.146, 0.067, 0.017, '
                                                        '0.000, 0.017, 0.067, 0.146, 0.250, 0.371, '
                                                        '0.500, 0.629, 0.750, 0.854, 0.933, 0.983, '
                                                        '1.000, 0.983, 0.933, 0.854, 0.750, 0.629]')

        self.default['heater']['channelType'] = '10v'
        self.default['heater']['stackLevel'] = '0'
        self.default['heater']['outputChannel'] = '4'
        self.default['heater']['gpioChannel'] = '23'
        self.default['heater']['loggingFrequency'] = '300'
        self.default['heater']['valueWhenReset'] = '0.'

        self.default['chiller']['channelType'] = 'pwm'
        self.default['chiller']['stackLevel'] = '0'
        self.default['chiller']['outputChannel'] = '4'
        self.default['chiller']['gpioChannel'] = 'None'
        self.default['chiller']['loggingFrequency'] = '300'
        self.default['chiller']['valueWhenReset'] = '0.'

        self.default['mfc.air']['stackLevel'] = '0'
        self.default['mfc.air']['inputChannel'] = '2'
        self.default['mfc.air']['channelType'] = 'volts'
        self.default['mfc.air']['parameterName'] = 'flow.mLperMin'
        self.default['mfc.air']['hardwareRange'] = '[0., 10000.]'
        self.default['mfc.air']['displayParameter'] = 'flow.mLperMin'
        self.default['mfc.air']['displayDecimals'] = '0'
        self.default['mfc.air']['sampleFrequency'] = '5'
        self.default['mfc.air']['loggingFrequency'] = '300'
        self.default['mfc.air']['offsetParameter'] = 'flow.mLperMin'
        self.default['mfc.air']['offsetDefault'] = '0.00'
        self.default['mfc.air']['validRange'] = '[0., 5000.]'
        self.default['mfc.air']['outputChannel'] = '1'
        self.default['mfc.air']['valueWhenReset'] = '500.'

        self.default['mfc.co2']['stackLevel'] = '0'
        self.default['mfc.co2']['inputChannel'] = '3'
        self.default['mfc.co2']['channelType'] = 'volts'
        self.default['mfc.co2']['parameterName'] = 'flow.mLperMin'
        self.default['mfc.co2']['hardwareRange'] = '[0.0, 40.0]'
        self.default['mfc.co2']['displayParameter'] = 'flow.mLperMin'
        self.default['mfc.co2']['displayDecimals'] = '1'
        self.default['mfc.co2']['sampleFrequency'] = '5'
        self.default['mfc.co2']['loggingFrequency'] = '300'
        self.default['mfc.co2']['offsetParameter'] = 'flow.mLperMin'
        self.default['mfc.co2']['offsetDefault'] = '0.000'
        self.default['mfc.co2']['validRange'] = '[0.0, 20.0]'
        self.default['mfc.co2']['outputChannel'] = '2'
        self.default['mfc.co2']['valueWhenReset'] = '0.'

        self.default['mfc.n2']['stackLevel'] = '0'
        self.default['mfc.n2']['inputChannel'] = '4'
        self.default['mfc.n2']['channelType'] = 'volts'
        self.default['mfc.n2']['parameterName'] = 'flow.mLperMin'
        self.default['mfc.n2']['hardwareRange'] = '[0., 2000.]'
        self.default['mfc.n2']['displayParameter'] = 'flow.mLperMin'
        self.default['mfc.n2']['displayDecimals'] = '0'
        self.default['mfc.n2']['sampleFrequency'] = '5'
        self.default['mfc.n2']['loggingFrequency'] = '300'
        self.default['mfc.n2']['offsetParameter'] = 'flow.mLperMin'
        self.default['mfc.n2']['offsetDefault'] = '0.00'
        self.default['mfc.n2']['validRange'] = '[0., 1000.]'
        self.default['mfc.n2']['outputChannel'] = '3'
        self.default['mfc.n2']['valueWhenReset'] = '0.'

    def validateConfig(self):

        # placeholder for allWidgets system-level array
        self.mainConfig['system']['allWidgets'] = []
        #print (f"{self.__class__.__name__}: Debug: allWidgets length [{len(self.mainConfig['system']['allWidgets'])}]")

        # system
        self.validate(bool, 'system', 'hideClockSeconds')
        self.validate(bool, 'system', 'clockTwoLines')
        self.validate(int,  'system', 'loggingFrequency', min=1)
        self.validate(int,  'system', 'memoryRetention',  min=300)

        # device
        self.validate(str, 'device', 'type')
        if self.mainConfig['device']['type'] not in ['tank', 'controller']:
            raise TypeError(f"{self.__class__.__name__}: ['device']['type'] = " +
                            f"[{self.mainConfig['device']['type']}] must be 'tank' or 'controller'")
        self.validate(str, 'device', 'id')

        # network
        self.validate(bool, 'network', 'enabled')
        self.validate(str,  'network', 'controllerIP')
        self.validate(str,  'network', 'ipNetworkStub')

        self.validateList(str, 'network', 'hardcoding')

        self.validate(int,  'network', 'updateFrequency', min=1)
        self.validate(int,  'network', 'lapseTime', min=1)

        # ipRange has some extra logic (non-decreasing order)
        self.validateList(int, 'network', 'ipRange', 2)
        if (self.mainConfig['network']['ipRange'] is not None
            and self.mainConfig['network']['ipRange'][0] > self.mainConfig['network']['ipRange'][1]):
            raise TypeError(f"{self.__class__.__name__}: ['network']['ipRange'] = " +
                            f"{self.mainConfig['network']['ipRange']} must specified in increasing order")

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
            if self.mainConfig[sensorType]['channelType'] not in ['volts', 'milliAmps']:
                raise TypeError(f"{self.__class__.__name__}: [sensorType]['channelType'] = " +
                                f"[{self.mainConfig[sensorType]['channelType']}] must be 'volts' or 'milliAmps'")

            # hardwareRange has some extra logic (non-decreasing order)
            self.validateList(float, sensorType, 'hardwareRange', 2)
            if (self.mainConfig[sensorType]['hardwareRange'] is not None
                and (  self.mainConfig[sensorType]['hardwareRange'][0]
                     > self.mainConfig[sensorType]['hardwareRange'][1])):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['hardwareRange'] = " +
                                f"{self.mainConfig[sensorType]['hardwareRange']} must specified in increasing order")

        # temperature, pH and DO comms parameters (serial port and baud rate)
        for sensorType in ['temperature', 'pH', 'DO']:
            self.validateSerialPort(sensorType, 'serialPort')
            self.validateBaudRate(sensorType, 'baudRate')

        # temperature, voltage, pH, DO and the MFCs share a lot of the same parameter logic
        for sensorType in ['temperature', 'voltage', 'pH', 'DO', 'mfc.air', 'mfc.co2', 'mfc.n2', 'generic']:

            # some sensors have hardwareRange as well as validRange
            if 'hardwareRange' in self.mainConfig[sensorType]:
                minVal = self.mainConfig[sensorType]['hardwareRange'][0]
                maxVal = self.mainConfig[sensorType]['hardwareRange'][1]
            else:
                minVal = None
                maxVal = None

            # validRange has some extra logic (non-decreasing order)
            self.validateList(float, sensorType, 'validRange', 2, min=minVal, max=maxVal)
            if (self.mainConfig[sensorType]['validRange'] is not None
                and self.mainConfig[sensorType]['validRange'][0] > self.mainConfig[sensorType]['validRange'][1]):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['validRange'] = " +
                                f"{self.mainConfig[sensorType]['validRange']} must specified in increasing order")

            self.validate(str,   sensorType, 'displayParameter')
            self.validate(int,   sensorType, 'displayDecimals',  min=0)
            self.validate(int,   sensorType, 'sampleFrequency',  min=1)
            self.validate(int,   sensorType, 'loggingFrequency', min=1)
            self.validate(str,   sensorType, 'offsetParameter')
            self.validate(float, sensorType, 'offsetDefault')

        # temperature, pH, and DO share the mode and setpoint-related logic
        for sensorType in ['temperature', 'pH', 'DO', 'generic']:

            # mode is specified in words in the config file, and converted to integer here
            self.validate(str, sensorType, 'modeNameDefault')
            if (self.mainConfig[sensorType]['modeNameDefault'].lower() not in MODES):
                raise TypeError(f"{self.__class__.__name__}: [{sensorType}]['modeNameDefault'] = " +
                                f"[{self.mainConfig[sensorType]['modeNameDefault']}] is not a " +
                                f"valid mode name.\nValid mode names are {MODES}.")

            # convert modeNameDefault to an integer
            self.mainConfig[sensorType]['modeDefault'] = MODES.index(self.mainConfig[sensorType]['modeNameDefault'].lower())

            # these are required to fall within the validRange for the sensor
            self.validate(float, sensorType, 'setpointDefault',   
                          min=self.mainConfig[sensorType]['validRange'][0],
                          max=self.mainConfig[sensorType]['validRange'][1])

            self.validateList(float, sensorType, 'dynamicDefault', 24,
                               min=self.mainConfig[sensorType]['validRange'][0],
                               max=self.mainConfig[sensorType]['validRange'][1])

        # the pH and DO subsystems require PID parameter values for their controls
        for sys in 'pH', 'DO':
            for param in 'Kp', 'Ki', 'Kd':
                for gas in 'air', 'co2', 'n2':
                    # only some combinations are valid
                    if ((gas == 'air') or (gas == 'co2' and sys == 'pH') or (gas == 'n2' and sys == 'DO')):
                        self.validate(float, sys, f"mfc.{gas}.{param}")

        # slight kludge: if 'DO' uses mgL instead of uM (default), rescale parameters and ranges
        if self.mainConfig['DO']['displayParameter'] == 'mgL':
            self.mainConfig['DO']['validRange'] = [ x * 15.9994 * 2. / 1000.
                                                    for x in self.mainConfig['DO']['validRange'] ]
            self.mainConfig['DO']['setpointDefault'] = self.mainConfig['DO']['setpointDefault'] * 15.9994 * 2. / 1000.
            self.mainConfig['DO']['dynamicDefault'] = [ x * 15.9994 * 2. / 1000.
                                                        for x in self.mainConfig['DO']['dynamicDefault'] ]

        # the virtual temperature sensor might be required even if not explicitly enabled
        self.mainConfig['virtualtemp'] = {**self.mainConfig['virtualtemp'], **self.mainConfig['temperature']}

        # heater/chiller parameters
        for controlType in ['heater', 'chiller']:

            # what type of output channel does the control use? pwm, 10v or gpio
            self.validate(str, controlType, 'channelType')
            if self.mainConfig[controlType]['channelType'] not in ['pwm', '10v', 'gpio']:
                raise TypeError(f"{self.__class__.__name__}: [controlType]['channelType'] = " +
                                f"[{self.mainConfig[controlType]['channelType']}] must be 'pwm', '10v' or 'gpio'")

            self.validate(int, controlType, 'stackLevel',    min=0, max=7)
            self.validate(int, controlType, 'outputChannel', min=1, max=4)
            self.validate(int, controlType, 'gpioChannel',   min=1, max=27)

            # heater and chiller have 0. or 1. as valid reset values
            self.validate(float, controlType, 'valueWhenReset')
            if self.mainConfig[controlType]['valueWhenReset'] not in [0., 1.]:
                raise TypeError(f"{self.__class__.__name__}: [{controlType}]['valueWhenReset'] = " +
                                f"{self.mainConfig[controlType]['valueWhenReset']} must be 0. or 1.")

        # controls (heater, chiller, mfc.air, mfc.co2, mfc.n2) share some parameter logic
        for controlType in ['heater', 'chiller', 'mfc.air', 'mfc.co2', 'mfc.n2']:
            self.validate(int, controlType, 'loggingFrequency', min=1)

        # MFCs (mfc.air, mfc.co2, mfc.n2) share some parameter logic
        for controlType in ['mfc.air', 'mfc.co2', 'mfc.n2']:

            self.validate(int, controlType, 'outputChannel', min=1, max=4)

            # the MFCs must merely have a reset value that falls within their validRange
            self.validate(float, controlType, 'valueWhenReset',
                          min=self.mainConfig[controlType]['validRange'][0],
                          max=self.mainConfig[controlType]['validRange'][1])

    def validate(self, cl, cat, param, min=None, max=None):

        #print (f"{self.__class__.__name__}: Debug: validate({cl.__name__},{cat},{param},{min},{max})")

        # pull value from system defaults if missing from the .conf file
        if param not in self.in_conf[cat]:
            self.in_conf[cat][param] = self.default[cat][param]

        # special case: None
        if self.in_conf[cat][param] == 'None':
            self.mainConfig[cat][param] = None
            return

        # attempt the conversion to the requested class
        try:
            # special handling for booleans
            if cl == bool:
                self.mainConfig[cat][param] = self.in_conf.getboolean(cat,param)
            else:
                self.mainConfig[cat][param] = cl(self.in_conf[cat][param])

            # if bounds are specified, check them
            if (   (min is not None and self.mainConfig[cat][param] < min)
                or (max is not None and self.mainConfig[cat][param] > max)):
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

            raise TypeError(f"{self.__class__.__name__}: [{cat}][{param}] = " +
                            f"[{self.in_conf[cat][param]}] is not {tp}{msg}") #from None


    def validateList(self, cl, cat, param, cnt=None, min=None, max=None):

        #print (f"{self.__class__.__name__}: Debug: validateList({cl.__name__},{cat},{param},{cnt},{min},{max})")

        # pull value from system defaults if missing from the .conf file
        if param not in self.in_conf[cat]:
            self.in_conf[cat][param] = self.default[cat][param]

        # special case: None
        if self.in_conf[cat][param] == 'None':
            self.mainConfig[cat][param] = None
            return

        # attempt the conversion to the requested class
        try:
            # convert a string that looks like a Python list into an actual Python list
            self.mainConfig[cat][param] = literal_eval(self.in_conf[cat][param])

            # is it a list?
            if type(self.mainConfig[cat][param]) is not list:
                raise

            # if length is specified, is it the expected length?
            if (    cnt is not None
                and len(self.mainConfig[cat][param]) != cnt):
                raise

            # explicitly convert values to requested class
            self.mainConfig[cat][param] = [ cl(x) if type(x) is not cl else x for x in self.mainConfig[cat][param] ]
            if len([ x for x in self.mainConfig[cat][param] if type(x) is not cl ]) > 0:
                raise

            # if bounds are specified, check them
            if (   (min is not None and len([ x for x in self.mainConfig[cat][param] if x < min ]) > 0)
                or (max is not None and len([ x for x in self.mainConfig[cat][param] if x > max ]) > 0)):
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

            raise TypeError(f"{self.__class__.__name__}: [{cat}][{param}] = "
                            f"{self.in_conf[cat][param]} is not a list of {tp}{msg}") from None

    def validateSerialPort(self, cat, param):

        # first, validate as string
        self.validate(str, cat, param)

        # if a serialPort is specified but doesn't exist on the system
        if self.mainConfig[cat][param] is not None:
            if not path.exists(self.mainConfig[cat][param]):

                # special logic for controllers: reset any missing serialPort to None
                if self.mainConfig['device']['type'] == 'controller':
                    self.mainConfig[cat][param] = None
                else:
                    raise TypeError(f"{self.__class__.__name__}: [{cat}][{param}] = "
                                    f"[{self.mainConfig[cat][param]}] does not exist on this system")

    def validateBaudRate(self, cat, param):

        # first, validate as integer
        self.validate(int, cat, param)

        # if a baud rate is specified but isn't found in the list of valid baud rates
        if (self.mainConfig[cat][param] is not None
            and self.mainConfig[cat][param] not in BAUDS):
            raise TypeError(f"{self.__class__.__name__}: [{cat}][{param}] = "
                            f"[{self.mainConfig[cat][param]}] is not a valid "
                            f"baud rate.\nValid baud rates are {BAUDS}.")

    # override [] syntax to return dictionaries of parameter values
    def __getitem__(self, key):
        return self.mainConfig[key]

def main():

    config = Erl2Config()
    print ("Erl2Config module (no GUI)")

if __name__ == "__main__": main()

