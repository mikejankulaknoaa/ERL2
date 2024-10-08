# the file-locking library is OS-dependent
try:
    import fcntl
    _pkg = "fcntl"
except:
    try:
        import msvcrt
        _pkg = "msvcrt"
    except:
        _pkg = None

import atexit
import os
import signal
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2Controller import Erl2Controller
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2State import Erl2State
from Erl2Tank import Erl2Tank
from Erl2Useful import locDefaults

class Erl2Startup:

    def __init__(self, erl2context={}):
        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # keep reference to startup module
        self.erl2context['startup'] = self

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # for graceful handling of termination and restart
        self.__restart = False

        # read this parameter from Erl2Config
        self.__deviceType = self.erl2context['conf']['device']['type']

        # identify the PID of this process
        self.__myPID = os.getpid()

        # file-locking only works if we loaded one of these packages
        assert _pkg in ("fcntl", "msvcrt")

        # try to get an exclusive lock on the PID file, if it exists
        self.__lockname = self.erl2context['conf']['system']['lockDir'] + '/Erl2Startup.pid'
        if os.path.isfile(self.__lockname):
            self.__lockfile = open(self.__lockname, 'r+')
            try:
                if _pkg == "fcntl":
                    fcntl.lockf(self.__lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif _pkg == "msvcrt":
                    msvcrt.locking(self.__lockfile.fileno(), msvcrt.LK_NBLCK, 1)
            except:
                # some OSes seem to disallow reading while locked
                try:
                    somePID = self.__lockfile.readline().rstrip()
                    errmsg = f"Cannot start Erl2Startup because PID [{somePID}] is already running"
                except:
                    errmsg = "Cannot start Erl2Startup because another process is already running"

                mb.showerror(title='Fatal Error', message=errmsg, parent=self.erl2context['root'])
                sys.exit()
            self.__lockfile.close()

        # reopen lockfile to write new PID
        self.__lockfile = open(self.__lockname, 'w')
        if _pkg == "fcntl":
            fcntl.lockf(self.__lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif _pkg == "msvcrt":
            msvcrt.locking(self.__lockfile.fileno(), msvcrt.LK_NBLCK, 1)
        self.__lockfile.write(str(self.__myPID))
        self.__lockfile.flush()

        # start a system log
        self.__systemLog = Erl2Log(logType='system', logName='Erl2Startup', erl2context=self.erl2context)
        self.__systemLog.writeMessage('Erl2Startup system startup')

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load some images that will be useful later on
        self.erl2context['img'].addImage('checkOff','checkbox-off-25.png')
        self.erl2context['img'].addImage('checkOn','checkbox-on-25.png')
        self.erl2context['img'].addImage('reload','reload-25.png')
        self.erl2context['img'].addImage('shutdown','shutdown-25.png')

        # we have a checkbox for changing between fullscreen and back
        self.__fullscreenVar = tk.IntVar()
        self.__fullscreenVar.set(self.erl2context['state'].get('system','fullscreen',1))

        # another checkbox is for enabling / disabling the Erl2NumPad popups
        self.__numPadVar = tk.IntVar()
        self.__numPadVar.set(self.erl2context['state'].get('system','numPad',1))

        # another checkbox is for enabling / disabling the matlibplot plots
        self.__plotsVar = tk.IntVar()
        self.__plotsVar.set(self.erl2context['state'].get('system','plots',1))

        # another checkbox is for enabling / disabling the summary logs
        self.__summaryLogsVar = tk.IntVar()
        self.__summaryLogsVar.set(self.erl2context['state'].get('system','summaryLogs',1))

        # location defaults for startup module, used in Erl2Tank and Erl2Controller
        self.modDefaults = {'relief'      : 'flat',
                            'borderwidth' : 0,
                            }

        # start up the main device module
        if self.__deviceType == 'tank':
            self.__device = Erl2Tank(erl2context=self.erl2context)
        elif self.__deviceType == 'controller':
            self.__device = Erl2Controller(erl2context=self.erl2context)

    def createFullscreenWidget (self, widgetLoc = {}):

        # nothing to do if no parent is given
        if 'parent' not in widgetLoc:
            return

        # read location parameter, set defaults if unspecified
        loc = locDefaults(loc=widgetLoc, modDefaults=self.modDefaults)

        # add a control to set / unset fullscreen mode
        self.fullscreenFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.fullscreenFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                                  padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])
        fullscreenCheckbutton = tk.Checkbutton(self.fullscreenFrame,
                                               indicatoron=0,
                                               image=self.erl2context['img']['checkOff'],
                                               selectimage=self.erl2context['img']['checkOn'],
                                               variable=self.__fullscreenVar,
                                               height=40,
                                               width=40,
                                               bd=0,
                                               highlightthickness=0,
                                               highlightcolor='#DBDBDB',
                                               background='#DBDBDB',
                                               highlightbackground='#DBDBDB',
                                               #bg='#DBDBDB',
                                               selectcolor='#DBDBDB',
                                               command=self.setFullscreen)
        fullscreenCheckbutton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(self.fullscreenFrame, text='Fullscreen', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.setFullscreen)

        self.fullscreenFrame.rowconfigure(0,weight=1)
        self.fullscreenFrame.columnconfigure(0,weight=0)
        self.fullscreenFrame.columnconfigure(1,weight=1)

    def createNumPadWidget (self, widgetLoc = {}):

        # nothing to do if no parent is given
        if 'parent' not in widgetLoc:
            return

        # read location parameter, set defaults if unspecified
        loc = locDefaults(loc=widgetLoc, modDefaults=self.modDefaults)

        # add a control to enable / disable the Erl2NumPad popups
        self.numPadFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.numPadFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                              padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])
        numPadCheckbutton = tk.Checkbutton(self.numPadFrame,
                                               indicatoron=0,
                                               image=self.erl2context['img']['checkOff'],
                                               selectimage=self.erl2context['img']['checkOn'],
                                               variable=self.__numPadVar,
                                               height=40,
                                               width=40,
                                               bd=0,
                                               highlightthickness=0,
                                               highlightcolor='#DBDBDB',
                                               background='#DBDBDB',
                                               highlightbackground='#DBDBDB',
                                               #bg='#DBDBDB',
                                               selectcolor='#DBDBDB',
                                               command=self.setNumPad)
        numPadCheckbutton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(self.numPadFrame, text='NumPad Popup', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.setNumPad)

        self.numPadFrame.rowconfigure(0,weight=1)
        self.numPadFrame.columnconfigure(0,weight=0)
        self.numPadFrame.columnconfigure(1,weight=1)

    def createPlotsWidget (self, widgetLoc = {}):

        # nothing to do if no parent is given
        if 'parent' not in widgetLoc:
            return

        # read location parameter, set defaults if unspecified
        loc = locDefaults(loc=widgetLoc, modDefaults=self.modDefaults)

        # add a control to enable / disable the matlibplot plots
        self.plotsFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.plotsFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                             padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])
        plotsCheckbutton = tk.Checkbutton(self.plotsFrame,
                                          indicatoron=0,
                                          image=self.erl2context['img']['checkOff'],
                                          selectimage=self.erl2context['img']['checkOn'],
                                          variable=self.__plotsVar,
                                          height=40,
                                          width=40,
                                          bd=0,
                                          highlightthickness=0,
                                          highlightcolor='#DBDBDB',
                                          background='#DBDBDB',
                                          highlightbackground='#DBDBDB',
                                          #bg='#DBDBDB',
                                          selectcolor='#DBDBDB',
                                          command=self.setPlots)
        plotsCheckbutton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(self.plotsFrame, text='Plots', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.setPlots)

        self.plotsFrame.rowconfigure(0,weight=1)
        self.plotsFrame.columnconfigure(0,weight=0)
        self.plotsFrame.columnconfigure(1,weight=1)

    def createSummaryLogsWidget (self, widgetLoc = {}):

        # nothing to do if no parent is given
        if 'parent' not in widgetLoc:
            return

        # read location parameter, set defaults if unspecified
        loc = locDefaults(loc=widgetLoc, modDefaults=self.modDefaults)

        # add a control to enable / disable the summary logs
        self.summaryLogsFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.summaryLogsFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                             padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])
        summaryLogsCheckbutton = tk.Checkbutton(self.summaryLogsFrame,
                                                indicatoron=0,
                                                image=self.erl2context['img']['checkOff'],
                                                selectimage=self.erl2context['img']['checkOn'],
                                                variable=self.__summaryLogsVar,
                                                height=40,
                                                width=40,
                                                bd=0,
                                                highlightthickness=0,
                                                highlightcolor='#DBDBDB',
                                                background='#DBDBDB',
                                                highlightbackground='#DBDBDB',
                                                #bg='#DBDBDB',
                                                selectcolor='#DBDBDB',
                                                command=self.setSummaryLogs)
        summaryLogsCheckbutton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(self.summaryLogsFrame, text='Summary Logs', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.setSummaryLogs)

        self.summaryLogsFrame.rowconfigure(0,weight=1)
        self.summaryLogsFrame.columnconfigure(0,weight=0)
        self.summaryLogsFrame.columnconfigure(1,weight=1)

    def createRestartWidget (self, widgetLoc = {}, widgetText='Restart ERL2'):

        # nothing to do if no parent is given
        if 'parent' not in widgetLoc:
            return

        # read location parameter, set defaults if unspecified
        loc = locDefaults(loc=widgetLoc, modDefaults=self.modDefaults)

        # add a control to restart the app
        self.restartFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.restartFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                               padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])
        restartButton = tk.Button(self.restartFrame,
                                  image=self.erl2context['img']['reload'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  background='#DBDBDB',
                                  activebackground='#DBDBDB',
                                  command=self.restartApp)
        restartButton.grid(row=0, column=0, padx='2 2', sticky='w')
        #restartButton.image = self.erl2context['img']['reload']
        l = ttk.Label(self.restartFrame, text=widgetText, font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.restartApp)

        self.restartFrame.rowconfigure(0,weight=1)
        self.restartFrame.columnconfigure(0,weight=0)
        self.restartFrame.columnconfigure(1,weight=1)

    def createExitWidget (self, widgetLoc = {}, widgetText='Shut down ERL2'):

        # nothing to do if no parent is given
        if 'parent' not in widgetLoc:
            return

        # read location parameter, set defaults if unspecified
        loc = locDefaults(loc=widgetLoc, modDefaults=self.modDefaults)

        # add a control to kill the app completely
        self.exitFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
        self.exitFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                            padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])
        exitButton = tk.Button(self.exitFrame,
                               image=self.erl2context['img']['shutdown'],
                               height=40,
                               width=40,
                               bd=0,
                               highlightthickness=0,
                               background='#DBDBDB',
                               activebackground='#DBDBDB',
                               command=self.exitApp)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(self.exitFrame, text=widgetText, font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.exitApp)

        self.exitFrame.rowconfigure(0,weight=1)
        self.exitFrame.columnconfigure(0,weight=0)
        self.exitFrame.columnconfigure(1,weight=1)

    # a method to toggle between fullscreen and regular window modes
    def setFullscreen(self, event=None):

        # first: if an event was passed, manually change the checkbox value
        if event is not None:
            self.__fullscreenVar.set(1-self.__fullscreenVar.get())

        # read the current state from the IntVar
        val = self.__fullscreenVar.get()

        # save the current state
        self.erl2context['state'].set([('system','fullscreen',val)])

        # apply requested state to window
        self.erl2context['root'].attributes('-fullscreen', bool(val))

    # a method to enable / disable the Erl2NumPad popups
    def setNumPad(self, event=None):

        # first: if an event was passed, manually change the checkbox value
        if event is not None:
            self.__numPadVar.set(1-self.__numPadVar.get())

        # update the state variable that controls whether Erl2NumPad opens
        self.erl2context['state'].set([('system','numPad',self.__numPadVar.get())])

    # a method to enable / disable the matplotlib plots
    def setPlots(self, event=None):

        # first: if an event was passed, manually change the checkbox value
        if event is not None:
            self.__plotsVar.set(1-self.__plotsVar.get())

        # update the state variable that controls whether matplotlib plots are drawn
        self.erl2context['state'].set([('system','plots',self.__plotsVar.get())])

    # a method to enable / disable the summary logs
    def setSummaryLogs(self, event=None):

        # first: if an event was passed, manually change the checkbox value
        if event is not None:
            self.__summaryLogsVar.set(1-self.__summaryLogsVar.get())

        # update the state variable that controls whether summary logs are updated
        self.erl2context['state'].set([('system','summaryLogs',self.__summaryLogsVar.get())])

    # restart the App
    def restartApp(self, event=None):

        # ask for confirmation
        if mb.askyesno('Restart Confirmation',
                       'Are you sure you want to restart the ERL2 App now?',
                       parent=self.erl2context['root']):

            # mention this in the log
            self.__systemLog.writeMessage('ERL2 system restart requested by GUI user')

            # terminate the current system and start it up again
            self.__restart = True
            self.gracefulExit()

    # shut down the App
    def exitApp(self, event=None):

        # ask for confirmation
        if mb.askyesno('Shut Down Confirmation',
                       'Are you sure you want to shut down the ERL2 App now?',
                       parent=self.erl2context['root']):

            # mention this in the log
            self.__systemLog.writeMessage('ERL2 system exit requested by GUI user')

            # terminate the system
            self.gracefulExit()

    # atexit.register() handler
    def atexitHandler(self):

        # make note in the logs if this event wasn't triggered by some other trapped signal
        if not self.erl2context['conf']['system']['shutdown']:
            self.__systemLog.writeMessage('Erl2Startup atexit handler triggered for App shutdown')

        # proceed with app termination
        self.gracefulExit()

    # signal handler
    def signalHandler(self, *args):

        # add a log entry to note any signals that were trapped
        if len(args) > 0:
            self.__systemLog.writeMessage(f"Erl2Startup trapped signal [{signal.Signals(args[0]).name}], exiting")

        # proceed with app termination
        self.gracefulExit()

    # for a graceful shutdown
    def gracefulExit(self):

        # avoid repeated calls to this handler
        if self.erl2context['conf']['system']['shutdown']:
            return
        self.erl2context['conf']['system']['shutdown'] = True

        # recursively call child handlers
        if hasattr(self.__device, 'gracefulExit') and callable(self.__device.gracefulExit):
            self.__device.gracefulExit()

        # terminate the current system and start it up again (if asked to do so)
        if self.__restart:
            python = sys.executable
            os.execv(python, ['python'] + sys.argv)

        # otherwise, just terminate the system
        else:
            #self.erl2context['root'].destroy() # this was leaving some .after() callbacks hanging
            tk.Tk.quit(self.erl2context['root'])

def main():

    root = tk.Tk()
    root.title("ERL2")
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    startup = Erl2Startup({'root':root})
    root.wait_visibility()
    startup.setFullscreen()

    # set things up for graceful termination
    atexit.register(startup.atexitHandler)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP,startup.signalHandler)
    signal.signal(signal.SIGINT,startup.signalHandler)
    signal.signal(signal.SIGTERM,startup.signalHandler)

    root.mainloop()

if __name__ == "__main__": main()

