from ast import literal_eval
from csv import reader,writer
from os import makedirs,path,remove,rename,stat
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log

class Erl2State():

    def __init__(self, erl2context={}):

        self.erl2context = erl2context

        # application state info is stored in nested dicts
        self.__erl2state = {}
        self.__dirName = None
        self.__fileName = None

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # state file is based on the location of the main logging directory
        try:
            # if there's no system-level log, reroute to a debug directory
            if 'system' not in Erl2Log.logTypes:
                self.__dirName = self.erl2context['conf']['system']['logDir'] + '/zDebug'
            else:
                self.__dirName = self.erl2context['conf']['system']['logDir']

            self.__fileName = self.__dirName + '/state.dat'

        except Exception as e:
            print (f"{self.__class__.__name__}: Error: Could not determine location of main logging directory: {e}")
            raise

        # initial directories
        if not path.isdir(self.erl2context['conf']['system']['logDir']):
            makedirs(self.erl2context['conf']['system']['logDir'])
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
                    if t not in self.__erl2state:
                        self.__erl2state[t] = {}

                    ## parse saved values to recover floats, lists, etc
                    #val = literal_eval(val)

                    # save the recovered value to state memory
                    self.__erl2state[t][n] = val

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
            types=list(self.__erl2state.keys())
            types.sort()
            for t in types:

                # loop through names in sorted order
                names=list(self.__erl2state[t].keys())
                names.sort()
                for n in names:

                    # extract the value from the dicts
                    val = self.__erl2state[t][n]

                    # write the value as a list
                    w.writerow([t,n,val])

    def get(self, type, name, defaultValue):

        # make sure the type dict exists
        if type not in self.__erl2state:
            self.__erl2state[type] = {}

        # add the setting's default value if it doesn't already exist
        if name not in self.__erl2state[type]:

            # note: populating a setting with its default doesn't trigger the state
            # to write out to file; it is only the changes to the defaults that need
            # to be remembered

            # always convert parameter values to strings
            self.__erl2state[type][name] = str(defaultValue)

        # and then parse the saved values to recover floats, lists etc.
        return literal_eval(self.__erl2state[type][name])

    def set(self, type, name, newValue):

        # make sure the type dict exists
        if type not in self.__erl2state:
            self.__erl2state[type] = {}

        #print (f"{self.__class__.__name__}: Debug: set({type},{name}) called: old [{str(self.__erl2state[type][name])}], new [{str(newValue)}]")

        # check if this setting is new, or exists and is changing
        if name not in self.__erl2state[type] or str(newValue) != self.__erl2state[type][name]:

            #print (f"{self.__class__.__name__}: Debug: set({type},{name},{newValue}) change detected!")

            # save the updated value to memory as a string
            self.__erl2state[type][name] = str(newValue)

            # save the updated value to disk
            self.writeToFile()

def main():

    state = Erl2State()
    print ("Erl2State module (no GUI)")

if __name__ == "__main__": main()

