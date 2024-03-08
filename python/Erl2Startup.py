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

class Erl2Startup:

    def __init__(self, root, erl2context={}):
        self.root = root
        self.erl2context = erl2context

        # for graceful handling of termination and restart
        self.__restart = False

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

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

                mb.showerror(title='Fatal Error', message=errmsg)
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

        # start up the main device module
        if self.__deviceType == 'tank':
            self.__device = Erl2Tank(root=self.root, parent=self, erl2context=self.erl2context)
        elif self.__deviceType == 'controller':
            self.__device = Erl2Controller(root=self.root, parent=self, erl2context=self.erl2context)

    def locDefaults (self, loc):

        # location defaults
        if 'padding'     in loc: p  = loc['padding']
        else:                    p  = '2 2'
        if 'relief'      in loc: rl = loc['relief']
        else:                    rl = 'flat'
        if 'borderwidth' in loc: bw = loc['borderwidth']
        else:                    bw = 0
        if 'row'         in loc: r  = loc['row']
        else:                    r  = 0
        if 'column'      in loc: c  = loc['column']
        else:                    c  = 0
        if 'padx'        in loc: px = loc['padx']
        else:                    px = '2'
        if 'pady'        in loc: py = loc['pady']
        else:                    py = '2'
        if 'sticky'      in loc: st = loc['sticky']
        else:                    st = 'nwse'

        return p, rl, bw, r, c, px, py, st,

    def createFullscreenWidget (self, loc = {}):

        # nothing to do if no parent is given
        if 'parent' not in loc:
            return

        # read location parameter, set defaults if unspecified
        p, rl, bw, r, c, px, py, st = self.locDefaults(loc)

        # add a control to set / unset fullscreen mode
        self.fullscreenFrame = ttk.Frame(loc['parent'], padding=p, relief=rl, borderwidth=bw)
        self.fullscreenFrame.grid(row=r, column=c, padx=px, pady=py, sticky=st)
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

    def createNumPadWidget (self, loc = {}):

        # nothing to do if no parent is given
        if 'parent' not in loc:
            return

        # read location parameter, set defaults if unspecified
        p, rl, bw, r, c, px, py, st = self.locDefaults(loc)

        # add a control to enable / disable the Erl2NumPad popups
        self.numPadFrame = ttk.Frame(loc['parent'], padding=p, relief=rl, borderwidth=bw)
        self.numPadFrame.grid(row=r, column=c, padx=px, pady=py, sticky=st)
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

    def createRestartWidget (self, loc = {}):

        # nothing to do if no parent is given
        if 'parent' not in loc:
            return

        # read location parameter, set defaults if unspecified
        p, rl, bw, r, c, px, py, st = self.locDefaults(loc)

        # add a control to restart the app
        self.restartFrame = ttk.Frame(loc['parent'], padding=p, relief=rl, borderwidth=bw)
        self.restartFrame.grid(row=r, column=c, padx=px, pady=py, sticky=st)
        restartButton = tk.Button(self.restartFrame,
                                  image=self.erl2context['img']['reload'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  activebackground='#DBDBDB',
                                  command=self.restartApp)
        restartButton.grid(row=0, column=0, padx='2 2', sticky='w')
        #restartButton.image = self.erl2context['img']['reload']
        l = ttk.Label(self.restartFrame, text='Restart ERL2', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.restartApp)

        self.restartFrame.rowconfigure(0,weight=1)
        self.restartFrame.columnconfigure(0,weight=0)
        self.restartFrame.columnconfigure(1,weight=1)

    def createExitWidget (self, loc = {}):

        # nothing to do if no parent is given
        if 'parent' not in loc:
            return

        # read location parameter, set defaults if unspecified
        p, rl, bw, r, c, px, py, st = self.locDefaults(loc)

        # add a control to kill the app completely
        self.exitFrame = ttk.Frame(loc['parent'], padding=p, relief=rl, borderwidth=bw)
        self.exitFrame.grid(row=r, column=c, padx=px, pady=py, sticky=st)
        exitButton = tk.Button(self.exitFrame,
                               image=self.erl2context['img']['shutdown'],
                               height=40,
                               width=40,
                               bd=0,
                               highlightthickness=0,
                               activebackground='#DBDBDB',
                               command=self.exitApp)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(self.exitFrame, text='Shut down ERL2', font='Arial 16'
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
        self.erl2context['state'].set('system','fullscreen',val)

        # apply requested state to window
        self.root.attributes('-fullscreen', bool(val))

    # a method to enable / disable the Erl2NumPad popups
    def setNumPad(self, event=None):

        # first: if an event was passed, manually change the checkbox value
        if event is not None:
            self.__numPadVar.set(1-self.__numPadVar.get())

        # update the state variable that controls whether Erl2NumPad opens
        self.erl2context['state'].set('system','numPad',self.__numPadVar.get())

    # restart the App
    def restartApp(self, event=None):

        # ask for confirmation
        if mb.askyesno('Restart Confirmation','Are you sure you want to restart the ERL2 App now?'):

            # mention this in the log
            self.__systemLog.writeMessage('ERL2 system restart requested by GUI user')

            # terminate the current system and start it up again
            self.__restart = True
            self.gracefulExit()

    # shut down the App
    def exitApp(self, event=None):

        # ask for confirmation
        if mb.askyesno('Shut Down Confirmation','Are you sure you want to shut down the ERL2 App now?'):

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
            os.execl(python, python, * sys.argv)

        # otherwise, just terminate the system
        else:
            #self.root.destroy() # this was leaving some .after() callbacks hanging
            print (f"{self.__class__.__name__}: Debug: calling tk.Tk.quit({self.root})")
            tk.Tk.quit(self.root)
            print (f"{self.__class__.__name__}: Debug: app did not quit!")

def main():

    root = tk.Tk()
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    startup = Erl2Startup(root)
    startup.setFullscreen()

    # set things up for graceful termination
    atexit.register(startup.atexitHandler)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP,startup.signalHandler)
    signal.signal(signal.SIGINT,startup.signalHandler)
    signal.signal(signal.SIGTERM,startup.signalHandler)

    root.mainloop()

if __name__ == "__main__": main()

