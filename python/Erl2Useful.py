# just a spot to collect useful constants + functions that don't need to belong to a class

from os import path,remove,rename

# control constants
OFFLINE=0
LOCAL=1
CONTROLLER=2

# mode constants
MANUAL=0
AUTO_STATIC=1
AUTO_DYNAMIC=2

# a list of choices for the mode radio buttons
MODEDICT = {MANUAL:'Manual',
            AUTO_STATIC:'Auto Static',
            AUTO_DYNAMIC:'Auto Dynamic'}

# hardcoded list of subSystems
SUBSYSTEMS = ['temperature', 'pH', 'DO']

# convenient way to avoid explicitly specifying .grid() parameters that are
# nearly always the same throughout Erl2

def locDefaults (loc={}, modDefaults={}):

    # Erl2-wide defaults if not specified
    returnVal = {'padding'    : '2 2',
                 'relief'     : 'solid',
                 'borderwidth': 1,
                 'row'        : 0,
                 'column'     : 0,
                 'rowspan'    : 1,
                 'columnspan' : 1,
                 'padx'       : '2',
                 'pady'       : '2',
                 'sticky'     : 'nesw',
                 }

    # module defaults, if specified, overwrite the ERL2-wide defaults
    returnVal.update(modDefaults)

    # anything specific to this ttk widget takes highest precedence
    returnVal.update(loc)

    # return the .grid() parameters
    return returnVal

# a timing calculation that gets done in lots of different Erl2 modules

def nextIntervalTime(currentTime, interval):

    retval = (
               (
                 int(
                   currentTime.timestamp() # timestamp in seconds
                   / interval              # convert to number of intervals of length loggingFrequency
                 )                         # truncate to beginning of previous interval (past)
               + 1)                        # advance by one time interval (future)
               * interval                  # convert back to seconds/timestamp
             )

    return retval

def moveFile(fromFile,toFile):

    # on windows you must first explicitly remove the file you're overwriting
    if path.isfile(toFile):
        remove(toFile)

    # now do the move (renaming)
    rename(fromFile, toFile)

