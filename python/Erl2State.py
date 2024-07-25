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

from csv import reader,writer
from datetime import datetime as dt
from datetime import timezone as tz
from json import dumps, loads
from os import makedirs,path,remove,rename
from re import findall, search
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2State():

    def __init__(self,
                 internalID='state',
                 fullPath=None,
                 readExisting=True,
                 memoryOnly=False,
                 erl2context={}):

        #if internalID == 'state':
        #    print (f"{self.__class__.__name__}: Debug: __init__(internalID={internalID},fullPath={fullPath},readExisting{readExisting}) called")

        # do not save erl2context as an attribute, it is only needed in __init__
        #self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in erl2context:
            erl2context['conf'] = Erl2Config()

        # trigger an error if the sync method (or fsync on windows) failed to load
        assert(_syncLoaded or (erl2context['conf']['system']['platform'] == 'win32' and _fsyncLoaded))

        # application state info is stored in nested dicts
        self.erl2state = {}
        self.__dirName = None
        self.__fileName = None
        self.__internalID = internalID
        self.__memoryOnly = memoryOnly

        # read these useful parameters from Erl2Config
        self.__dtFormat = erl2context['conf']['system']['dtFormat']
        self.__dtRegexp = erl2context['conf']['system']['dtRegexp']

        # fullPath parameter is allowed to override the default file name and location
        if fullPath is not None:
            self.__dirName = path.dirname(fullPath)
            self.__fileName = fullPath

        # otherwise use the default file name/location logic
        else:
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

        # if file exists, reload saved state from file (unless asked not to)
        if readExisting:
            self.readFromFile()

    def readFromFile(self):

        # monitor our progress
        sizeDat = sizeBak = sizeLck = None
        valuesRead = 0
        if path.isfile(self.__fileName):
            sizeDat = path.getsize(self.__fileName)
        if path.isfile(self.__fileName + '.bak'):
            sizeBak = path.getsize(self.__fileName + '.bak')
        if path.isfile(self.__fileName + '.lck'):
            sizeLck = path.getsize(self.__fileName + '.lck')

        #if self.__internalID == 'state':
        #    print (f"{self.__class__.__name__}: Debug: readFromFile({self.__fileName}) called: sizeDat [{sizeDat}], sizeBak [{sizeBak}], sizeLck [{sizeLck}]]")

        # if there's an orphaned lock file, and backup exists, restore it
        if sizeLck is not None and sizeBak is not None and sizeBak > 0:
            print (f"{self.__class__.__name__}: Warning: readFromFile({self.__fileName}): found .lck, restoring from .bak file")
            self.moveFile(self.__fileName + '.bak', self.__fileName)
            remove(self.__fileName + '.lck')

        # otherwise if there's no .dat file, just give up
        if sizeDat is None:
            print (f"{self.__class__.__name__}: Warning: readFromFile({self.__fileName}) aborting, no .dat file found")
            return

        # if the main file is of zero size, try pivoting to the backup file
        if sizeDat == 0 and sizeBak is not None and sizeBak > 0:

            print (f"{self.__class__.__name__}: Warning: readFromFile({self.__fileName}): .dat file empty, restoring from .bak file")
            self.moveFile(self.__fileName + '.bak', self.__fileName)

        # keep looping until all options exhausted
        keepLooping = True
        while keepLooping:

            # optimism!
            keepLooping = False

            # open the state file for reading
            with open(self.__fileName, 'r', newline='') as f:
                r = reader(f, dialect='unix')

                # loop through lines in the file
                for row in r:

                    # unpacking this row depends on there being three columns
                    if len(row) == 3:

                        # type, name, value
                        t, n, val = row

                        # make sure the top-level type dict exists
                        if t not in self.erl2state:
                            self.erl2state[t] = {}

                        # save the recovered value to state memory
                        self.erl2state[t][n] = val
                        valuesRead += 1

                    # this means at least one line in the state files is corrupted
                    else:
                        # close the file we're currently reading
                        f.close()

                        # note: I'm not going to erase any parameters that were loaded from the corrupted file
                        # (anyhow if it's corrupted, then probably the whole thing is unreadable)

                        # keep a copy of the corrupted file for posterity
                        self.moveFile(self.__fileName, self.__fileName + '.err')

                        # is there a backup file we can try?
                        if sizeBak is not None and sizeBak > 0:
                            print (f"{self.__class__.__name__}: Warning: readFromFile({self.__fileName}): .dat file corrupted, restoring from .bak file")
                            self.moveFile(self.__fileName + '.bak', self.__fileName)
                            sizeDat = sizeBak
                            sizeBak = None

                            # we're not out of options yet
                            keepLooping = True

                        else:
                            print (f"{self.__class__.__name__}: Warning: readFromFile({self.__fileName}): .dat file corrupted, no backup available")

                        # no reason to keep reading this corrupted file
                        break

        #if self.__internalID == 'state':
        #    print (f"{self.__class__.__name__}: Debug: readFromFile({self.__fileName}) finished: valuesRead [{valuesRead}]")

    def writeToFile(self):

        # doesn't apply if this instance is memoryOnly
        if self.__memoryOnly:
            return

        #print (f"{self.__class__.__name__}: Debug: writeToFile({self.__fileName}) called")

        # open and close a lock file to track if this method finished correctly
        with open(self.__fileName + '.lck', 'w') as f:
            pass

        # if it exists, rename the old file instead of overwriting
        if path.isfile(self.__fileName) and path.getsize(self.__fileName) > 0:
            self.moveFile(self.__fileName, self.__fileName + '.bak')

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

                    # don't buffer the output stream, in case of irregular app termination
                    f.flush()

                    # force python to write changes to disk (windows)
                    if _fsyncLoaded:
                        fsync(f.fileno())

        # force python to write changes to disk (non-windows)
        if _syncLoaded:
            sync()

        # delete the lock file
        if path.isfile(self.__fileName + '.lck'):
            remove(self.__fileName + '.lck')

        #print (f"{self.__class__.__name__}: Debug: writeToFile({self.__fileName}) finished as expected")

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

    def getall(self):

        #print (f"{self.__class__.__name__}: Debug: getall() called")

        valueList = []

        # loop through all types
        for tp in self.erl2state.keys():

            # loop through all names
            for nm in self.erl2state[tp].keys():

                # add this 3-tuple, including the decoded value, to the list
                valueList.append((tp, nm, self.decode(self.erl2state[tp][nm])))

        # return the resulting valueList
        return valueList

    def set(self, valueList=[]):

        #print (f"{self.__class__.__name__}: Debug: set({valueList}) called")

        # remember if there's any reason to write out the file to disk again
        writeNow = False

        # valueList is a list of 3-tuples; allow update to multiple values at once
        # to avoid writing and rewriting to disk during a series of related changes
        for tpl in valueList:

            # enforce assumptions about argument types
            if type(tpl) is not tuple or len(tpl) != 3:
                raise TypeError(f"{self.__class__.__name__}: valueList {valueList} is not a list of 3-tuples")

            # unpack the tuple into individual arguments
            valueType, valueName, newValue = tpl

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

                # remember to save these changes to disk when all finished
                writeNow = True


        # were there any changes we need to write to disk?
        if writeNow:
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

    # this method REPLACES any existing settings with the new set
    def assign(self,fromState):

        # something is very wrong if this argument is the wrong type
        assert type(fromState) is Erl2State

        # overwrite whatever is currently stored in this instance
        self.erl2state = fromState.erl2state.copy()

        # save the updated values to disk
        self.writeToFile()

    # this method AUGMENTS any existing settings with the new set
    def add(self,fromState):

        # something is very wrong if this argument is the wrong type
        assert type(fromState) is Erl2State

        # get all values at once and send them to set() to be added
        self.set(fromState.getall())

    def isType(self,valueType):

        return type(self.erl2state) is dict and valueType in self.erl2state

    def isName(self,valueType, valueName):

        return type(self.erl2state) is dict and valueType in self.erl2state and valueName in self.erl2state[valueType]

    def moveFile(self,fromFile,toFile):

        # on windows you must first explicitly remove the file you're overwriting
        if path.isfile(toFile):
            remove(toFile)

        # now do the move (renaming)
        rename(fromFile, toFile)

def main():

    state = Erl2State()
    print ("Erl2State module (no GUI)")

if __name__ == "__main__": main()

