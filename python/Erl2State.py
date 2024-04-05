from csv import reader,writer
from datetime import datetime as dt
from datetime import timezone as tz
from json import dumps, loads
from os import makedirs,path,remove,rename,stat
from re import findall, search
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2State():

    def __init__(self, internalID='state', erl2context={}):

        # do not save erl2context as an attribute, it is only needed in __init__
        #self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in erl2context:
            erl2context['conf'] = Erl2Config()

        # application state info is stored in nested dicts
        self.erl2state = {}
        self.__dirName = None
        self.__fileName = None

        # read these useful parameters from Erl2Config
        self.__dtFormat = erl2context['conf']['system']['dtFormat']
        self.__dtRegexp = erl2context['conf']['system']['dtRegexp']

        # state file is based on the location of the main logging directory
        try:
            # if there's no system-level log, reroute to a debug directory
            if 'system' not in Erl2Log.logTypes:
                self.__dirName = erl2context['conf']['system']['logDir'] + '/zDebug/state'
            else:
                self.__dirName = erl2context['conf']['system']['logDir'] + '/state'

            # name the file according to the internal ID (default: 'state.dat')
            self.__fileName = self.__dirName + '/' + internalID + '.dat'

        except Exception as e:
            print (f"{self.__class__.__name__}: Error: Could not determine location of main logging directory: {e}")
            raise

        # initial directories
        if not path.isdir(erl2context['conf']['system']['logDir']):
            makedirs(erl2context['conf']['system']['logDir'])
        if not path.isdir(self.__dirName):
            makedirs(self.__dirName)

        # if file exists, reload saved state from file
        self.readFromFile()

    def readFromFile(self):

        # if there's a state file left over from a previous run
        if path.isfile(self.__fileName) and stat(self.__fileName).st_size > 0:

            # open the state file for reading
            with open(self.__fileName, 'r', newline='') as f:
                r = reader(f, dialect='unix')

                # loop through lines in the file
                for t, n, val in r:

                    # make sure the top-level type dict exists
                    if t not in self.erl2state:
                        self.erl2state[t] = {}

                    # save the recovered value to state memory
                    self.erl2state[t][n] = val

    def writeToFile(self):

        # if it exists, rename the old file instead of overwriting
        if path.isfile(self.__fileName) and stat(self.__fileName).st_size > 0:

            # on windows you must first explicitly remove the old .bak file
            if path.isfile(self.__fileName + '.bak'):
                remove(self.__fileName + '.bak')

            # now rename the current state file before creating the new one
            rename(self.__fileName, self.__fileName + '.bak')

        # open the state file for writing
        with open(self.__fileName, 'w', newline='') as f:
            w = writer(f, dialect='unix')

            # loop through top-level types in sorted order
            types=list(self.erl2state.keys())
            types.sort()
            for t in types:

                # loop through names in sorted order
                names=list(self.erl2state[t].keys())
                names.sort()
                for n in names:

                    # extract the value from the dicts
                    val = self.erl2state[t][n]

                    # write the value as a list
                    w.writerow([t,n,val])

    def get(self, valueType, valueName, defaultValue):

        #print (f"{self.__class__.__name__}: Debug: get({valueType},{valueName},{defaultValue}) called")

        readValue = None

        # make sure the type dict exists
        if valueType not in self.erl2state:
            self.erl2state[valueType] = {}

        # add the setting's default value if it doesn't already exist
        if valueName not in self.erl2state[valueType]:

            # note: populating a setting with its default doesn't trigger the state
            # to write out to file; it is only the changes to the defaults that need
            # to be remembered

            # always encode parameter values
            self.erl2state[valueType][valueName] = self.encode(defaultValue)

        # decode the saved parameter value
        readValue = self.decode(self.erl2state[valueType][valueName])

        #print (f"{self.__class__.__name__}: Debug: get({valueType},{valueName},{defaultValue}) returning: {str(readValue)}")

        # return the decoded value
        return readValue

    def set(self, valueType, valueName, newValue):

        #print (f"{self.__class__.__name__}: Debug: set({valueType},{valueName},{newValue}) called")

        # make sure the type dict exists
        if valueType not in self.erl2state:
            self.erl2state[valueType] = {}

        # support encoding of more complex data types
        writeValue = self.encode(newValue)

        # check if this setting is new, or exists and is changing
        if valueName not in self.erl2state[valueType] or writeValue != self.erl2state[valueType][valueName]:

            #if valueName not in self.erl2state[valueType]: old = None
            #else: old = self.erl2state[valueType][valueName]
            #print (f"{self.__class__.__name__}: Debug: set({valueType},{valueName},<newValue>) setting: old {old}, new {writeValue}")

            # save the updated value to memory as an encoded string
            self.erl2state[valueType][valueName] = writeValue

            # save the updated value to disk
            self.writeToFile()

    def decode(self, val):

        #print (f"{self.__class__.__name__}: Debug: decode called with {val}")

        # initialize return value
        returnValue = val

        # encoding mistakes sometimes write empty strings, so avoid crashes
        if returnValue is None or returnValue == '':
            #print (f"{self.__class__.__name__}: Debug: decode returning None")
            returnValue = None
        else:

            # test if this was encoded for datetimes
            mat = search(r'^{ERL2TS}(.*)$',returnValue)

            # simple case: no encoding
            if not mat:
                #print (f"{self.__class__.__name__}: Debug: decode: simple case: loads({returnValue})")
                returnValue = loads(returnValue)

            else:
                # get encoded value without the header
                returnValue = mat.groups()[0]

                # another simple case: just a datetime string
                if search(self.__dtRegexp, returnValue):
                    #print (f"{self.__class__.__name__}: Debug: decode returning a datetime")
                    returnValue = dt.strptime(returnValue, self.__dtFormat).replace(tzinfo=tz.utc)

                else:
                    # how many encodings remain?
                    #seeking = len(findall(r'{ERL2TS}',returnValue))

                    # reconstitute whatever kind of datatype this was
                    #print (f"{self.__class__.__name__}: Debug: decode: reconstitute: loads({returnValue})")
                    returnValue = loads(returnValue)

                    # if a list, iterate looking for more encodings
                    if type(returnValue) is list:
                        for ind in range(0,len(returnValue)):

                            # recursively call the decode method
                            returnValue[ind] = self.decode(returnValue[ind])

                    # step through dict key values
                    elif type(returnValue) is dict:
                        for key in returnValue:

                            # recursively call the decode method
                            returnValue[key] = self.decode(returnValue[key])

                    # this shouldn't be possible
                    else:
                        raise TypeError(f"{self.__class__.__name__}: decode TypeError: type [{type(returnValue)}] unexpected")

        #print (f"{self.__class__.__name__}: Debug: decode returning [{type(returnValue)}]")
        return returnValue

    def encode(self, val):

        # json works for most cases except when datetimes are involved
        try:
            #print (f"{self.__class__.__name__}: Debug: decode: first try: dumps({val})")
            return dumps(val)

        # if it's a datetime error, try encoding datetimes
        except TypeError as e:
            if str(e) == 'Object of type datetime is not JSON serializable':

                # simple case: a single timestamp value
                if type(val) is dt:
                    return '{ERL2TS}' + val.strftime(self.__dtFormat)

                # also supports some more complex data types
                elif hasattr(val,'copy'):

                    # avoid changing values in place
                    tempVal = val.copy()

                    # iterate through list values
                    if type(tempVal) is list:
                        for ind in range(0,len(list)):

                            # recursively call the encode method
                            tempVal[ind] = self.encode(tempVal[ind])

                        # return modified encoding and flag it
                        #print (f"{self.__class__.__name__}: Debug: decode: list[{ind}]: dumps({tempVal})")
                        return '{ERL2TS}' + dumps(tempVal)

                    # step through dict key values
                    elif type(tempVal) is dict:
                        for key in tempVal:

                            # recursively call the encode method
                            tempVal[key] = self.encode(tempVal[key])

                        # return modified encoding and flag it
                        #print (f"{self.__class__.__name__}: Debug: decode: dict[{key}]: dumps({tempVal})")
                        return '{ERL2TS}' + dumps(tempVal)

            # if we reached this point then we couldn't overcome the TypeError
            raise TypeError(f"{self.__class__.__name__}: encode TypeError: type [{type(val)}] not supported")

    def assign(self,fromState):

        # something is very wrong if this argument is the wrong type
        assert type(fromState) is Erl2State

        # overwrite whatever is currently stored in this instance
        self.erl2state = fromState.erl2state.copy()

        # save the updated values to disk
        self.writeToFile()

def main():

    state = Erl2State()
    print ("Erl2State module (no GUI)")

if __name__ == "__main__": main()

