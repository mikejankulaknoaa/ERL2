#! /usr/bin/python3

import atexit
from datetime import datetime as dt
from datetime import timezone as tz
import fcntl
import os
import signal
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Chiller import Erl2Chiller
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Heater import Erl2Heater
from Erl2Image import Erl2Image
from Erl2Input import Erl2Input
from Erl2Log import Erl2Log
from Erl2Mfc import Erl2Mfc
from Erl2Network import Erl2Network
from Erl2Pyro import Erl2Pyro
from Erl2State import Erl2State
from Erl2SubSystem import Erl2SubSystem
from Erl2VirtualTemp import Erl2VirtualTemp

class Erl2Tank:

    def __init__(self, parent, erl2context={}):
        self.__parent = parent
        self.erl2context = erl2context

        # for graceful handling of termination and restart
        self.__restart = False

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # identify the PID of this process
        self.__myPID = os.getpid()

        # try to get an exclusive lock on the PID file, if it exists
        self.__lockname = self.erl2context['conf']['system']['lockDir'] + '/Erl2Tank.pid'
        if os.path.isfile(self.__lockname):
            self.__lockfile = open(self.__lockname, 'r+')
            try:
                fcntl.lockf(self.__lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except:
                somePID = self.__lockfile.readline().rstrip()
                mb.showerror(title='Fatal Error', message=f"Cannot start Erl2Tank because PID [{somePID}] is already running")
                sys.exit()
            self.__lockfile.close()

        # reopen lockfile to write new PID
        self.__lockfile = open(self.__lockname, 'w')
        fcntl.lockf(self.__lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.__lockfile.write(str(self.__myPID))
        self.__lockfile.flush()

        # start a system log
        self.__systemLog = Erl2Log(logType='system', logName='Erl2Tank', erl2context=self.erl2context)
        self.__systemLog.writeMessage('Erl2Tank system startup')

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load some images that will be useful later on
        self.erl2context['img'].addImage('checkOff','checkbox-off-25.png')
        self.erl2context['img'].addImage('checkOn','checkbox-on-25.png')
        self.erl2context['img'].addImage('reload','reload-25.png')
        self.erl2context['img'].addImage('shutdown','shutdown-25.png')

        # stylistic stuff
        s = ttk.Style()
        s.configure('TNotebook',tabposition='nw',borderwidth=1,relief='solid')
        s.configure('TNotebook.Tab',font='Arial 16 italic',borderwidth=1,relief='solid',padding='3 3',tabmargins='2 2 2 0',width=8)
        s.configure('TRadiobutton',font='Arial 16')

        # these dicts will hold the objects in this module
        self.__tabs = {}
        self.__frames = {}
        self.sensors = {}
        self.controls = {}
        self.systems = {}

        # remember if network module is active
        self.network = None

        # we have a checkbox for changing between fullscreen and back
        self.__fullscreenVar = tk.IntVar()
        self.__fullscreenVar.set(self.erl2context['state'].get('system','fullscreen',1))

        # another checkbox is for enabling / disabling the Erl2NumPad popups
        self.__numPadVar = tk.IntVar()
        self.__numPadVar.set(self.erl2context['state'].get('system','numPad',1))

        # the top-level element is a notebook (tabbed screens)
        self.__mainTabs = ttk.Notebook(self.__parent,padding='5 5 5 2')
        self.__mainTabs.grid(row=0,column=0,pady='0',sticky='nesw')
        self.__mainTabs.rowconfigure(0,weight=1)
        self.__mainTabs.columnconfigure(0,weight=1)

        # trap the tab-change event for special handling
        self.__mainTabs.bind('<<NotebookTabChanged>>',self.changeTabs)

        # currently we have five tabs
        self.__tabNames = ['Data', 'Temp', 'pH', 'DO', 'Settings']

        # create the tabbed pages (five of them)
        for p in self.__tabNames:

            self.__tabs[p] = ttk.Frame(self.__mainTabs, padding='0',borderwidth=0,relief='solid')
            self.__tabs[p].grid_rowconfigure(0,weight=1)
            self.__tabs[p].grid_columnconfigure(0,weight=1)
            self.__mainTabs.add(self.__tabs[p],text=p,padding=0)

        # add a clock widget in the upper right corner
        clock = Erl2Clock(clockLoc={'parent':self.__parent,'row':0,'column':0},
                          erl2context=self.erl2context)

        # quickly create 3x4 grids of frames in all tabs except Settings
        for p in [x for x in self.__tabNames if x != 'Settings']:
            self.__frames[p] = {}
            for r in range(3):
                self.__frames[p][r] = {}
                for c in range(4):

                    # some pages have frames that span more than one row or column
                    if (p in ['Temp','pH','DO'] and r==0 and c==3):
                        self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                        self.__frames[p][r][c].grid(row=r, column=c, rowspan=2, padx='2', pady='2', sticky='nesw')
                    #elif (p in ['Temp','pH','DO'] and r==1 and c==0):
                    #    self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                    #    self.__frames[p][r][c].grid(row=r, column=c, columnspan=2, padx='2', pady='2', sticky='nesw')
                    elif (p in ['Temp','pH','DO'] and r==2 and c==0):
                        self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                        self.__frames[p][r][c].grid(row=r, column=c, columnspan=4, padx='2', pady='2', sticky='nesw')
                    #elif (p in ['Temp','pH','DO'] and (r,c) in [(1,1),(1,3),(2,1),(2,2),(2,3)]):
                    #    pass
                    elif (p in ['Temp','pH','DO'] and (r,c) in [(1,3),(2,1),(2,2),(2,3)]):
                        pass
                    else:
                        self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                        self.__frames[p][r][c].grid(row=r, column=c, padx='2', pady='2', sticky='nesw')

            # after everything is created, set row weights...
            for r in range(3):
                self.__tabs[p].rowconfigure(r, weight=1)

            # ...and column weights
            for c in range(4):
               self.__tabs[p].columnconfigure(c, weight=1)

        # but afterwards, overwrite column weights in the Data tab to squeeze three of the columns
        self.__tabs['Data'].columnconfigure(0,weight=0)
        self.__tabs['Data'].columnconfigure(1,weight=0)
        self.__tabs['Data'].columnconfigure(3,weight=0)

        # for Settings, just create three frames for now
        self.__frames['Settings'] = {}
        for r in range(2):
            self.__frames['Settings'][r] = {}
            self.__frames['Settings'][r][0] = ttk.Frame(self.__tabs['Settings'], padding='2', relief='solid', borderwidth=1)
            self.__frames['Settings'][r][0].grid(row=r, column=0, padx='2', pady='2', sticky='nesw')
        self.__frames['Settings'][0][1] = ttk.Frame(self.__tabs['Settings'], padding='2', relief='solid', borderwidth=1)
        self.__frames['Settings'][0][1].grid(row=0, column=1, rowspan=2, padx='2', pady='2', sticky='nesw')

        self.__tabs['Settings'].rowconfigure(0,weight=1)
        self.__tabs['Settings'].rowconfigure(1,weight=0)
        self.__tabs['Settings'].columnconfigure(0,weight=0)
        self.__tabs['Settings'].columnconfigure(1,weight=1)

        # I need some placeholder text for the Error Report frames
        dummyError = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed'
        dummyError += ' do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
        dummyError += ' Ut enim ad minim veniam, quis nostrud exercitation ullamco'
        dummyError += ' laboris nisi ut aliquip ex ea commodo consequat.'
        dummyError += ' Duis aute irure dolor in reprehenderit in voluptate velit'
        dummyError += ' esse cillum'
        #dummyError += ' dolore eu fugiat nulla pariatur.'
        #dummyError += ' Excepteur sint occaecat cupidatat non proident, sunt in'
        #dummyError += ' culpa qui officia deserunt mollit anim id est laborum.'

        # labels for the frames in the Settings tab
        ttk.Label(self.__frames['Settings'][0][0], text='Preferences', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['Settings'][1][0], text='Power', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['Settings'][0][1], text='About ERL2', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')

        # information about this ERL2 system
        fontleft = 'Arial 14 bold'
        fontright = 'Arial 14'

        r = 1
        ttk.Label(self.__frames['Settings'][0][1], text='ERL2 Version:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2context['conf']['system']['version'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Device Id:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2context['conf']['device']['id'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Log Directory:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2context['conf']['system']['logDir'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Logging Frequency:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')

        # elegant way to summarize logging frequency info
        freq = {}
        for sens in ['temperature', 'pH', 'DO', 'heater', 'chiller', 'mfc.air', 'mfc.co2', 'mfc.n2']:
            if self.erl2context['conf'][sens]['loggingFrequency'] not in freq:
                freq[self.erl2context['conf'][sens]['loggingFrequency']] = [sens]
            else:
                freq[self.erl2context['conf'][sens]['loggingFrequency']].append(sens)
        if len(freq) == 1:
            txt = str(self.erl2context['conf']['temperature']['loggingFrequency']) + ' seconds'
        else:
            txt = ""
            num = 0
            for k, v in sorted(freq.items(), key=lambda item: len(item[1])):
                num += 1
                if num < len(freq):
                    txt += f"{', '.join(v)}: {k} seconds; "
                else:
                    txt += f"other sensors: {k} seconds"

        ttk.Label(self.__frames['Settings'][0][1], text=txt, font=fontright, wraplength=300
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='System Startup:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2context['conf']['system']['startup'].astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='System Timezone:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=str(self.erl2context['conf']['system']['timezone']), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Temperature Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        tempStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        if self.erl2context['conf']['virtualtemp']['enabled']:
            r += 1
            ttk.Label(self.__frames['Settings'][0][1], text='-- using Virtual Temperature --', font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='pH Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        pHStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='DO Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        doStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Air MFC Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        airMfcStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='CO2 MFC Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        co2MfcStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='N2 MFC Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        n2MfcStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        # if necessary, include networking details
        if self.erl2context['conf']['network']['tankNetwork']:
            r += 1
            ttk.Label(self.__frames['Settings'][0][1], text='IP Address:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ipLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

            r += 1
            ttk.Label(self.__frames['Settings'][0][1], text='MAC Address:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            macLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

            r += 1
            ttk.Label(self.__frames['Settings'][0][1], text='Last Network Comms:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            netStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        else:
            # dummy row at end
            r += 1
            ttk.Label(self.__frames['Settings'][0][1], text='this space intentionally left blank', font='Arial 12'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, columnspan=2, sticky='s')

        for row in range(r-1):
            self.__frames['Settings'][0][1].rowconfigure(row,weight=0)
        self.__frames['Settings'][0][1].rowconfigure(r,weight=1)
        self.__frames['Settings'][0][1].columnconfigure(0,weight=1)
        self.__frames['Settings'][0][1].columnconfigure(1,weight=1)

        # add a control to set / unset fullscreen mode
        r = 1
        fullscreenFrame = ttk.Frame(self.__frames['Settings'][0][0], padding='2 2', relief='flat', borderwidth=0)
        fullscreenFrame.grid(row=r, column=0, padx='2', pady='2', sticky='nwse')
        fullscreenCheckbutton = tk.Checkbutton(fullscreenFrame,
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
        l = ttk.Label(fullscreenFrame, text='Fullscreen', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.setFullscreen)

        fullscreenFrame.rowconfigure(0,weight=1)
        fullscreenFrame.columnconfigure(0,weight=0)
        fullscreenFrame.columnconfigure(1,weight=1)

        # add a control to enable / disable the Erl2NumPad popups
        r += 1
        numPadFrame = ttk.Frame(self.__frames['Settings'][0][0], padding='2 2', relief='flat', borderwidth=0)
        numPadFrame.grid(row=r, column=0, padx='2', pady='2', sticky='nwse')
        numPadCheckbutton = tk.Checkbutton(numPadFrame,
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
        l = ttk.Label(numPadFrame, text='NumPad Popup', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.setNumPad)

        numPadFrame.rowconfigure(0,weight=1)
        numPadFrame.columnconfigure(0,weight=0)
        numPadFrame.columnconfigure(1,weight=1)

        # restart the app
        restartFrame = ttk.Frame(self.__frames['Settings'][1][0], padding='2 2', relief='flat', borderwidth=0)
        restartFrame.grid(row=1, column=0, padx='2', pady='2', sticky='nwse')
        restartButton = tk.Button(restartFrame,
                                  image=self.erl2context['img']['reload'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  activebackground='#DBDBDB',
                                  command=self.restartApp)
        restartButton.grid(row=0, column=0, padx='2 2', sticky='w')
        #restartButton.image = self.erl2context['img']['reload']
        l = ttk.Label(restartFrame, text='Restart ERL2', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.restartApp)

        restartFrame.rowconfigure(0,weight=1)
        restartFrame.columnconfigure(0,weight=0)
        restartFrame.columnconfigure(1,weight=1)

        # kill the app completely with this shutdown button
        exitFrame = ttk.Frame(self.__frames['Settings'][1][0], padding='2 2', relief='flat', borderwidth=0)
        exitFrame.grid(row=2, column=0, padx='2', pady='2', sticky='nwse')
        exitButton = tk.Button(exitFrame,
                               image=self.erl2context['img']['shutdown'],
                               height=40,
                               width=40,
                               bd=0,
                               highlightthickness=0,
                               activebackground='#DBDBDB',
                               command=self.exitApp)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(exitFrame, text='Shut down ERL2', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.exitApp)

        exitFrame.rowconfigure(0,weight=1)
        exitFrame.columnconfigure(0,weight=0)
        exitFrame.columnconfigure(1,weight=1)

        # readout displays for the current temperature (real or virtual)
        if self.erl2context['conf']['virtualtemp']['enabled']:
            self.sensors['temperature'] = Erl2VirtualTemp(
                parent=self,
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                correctionLoc={'parent':self.__frames['Temp'][0][2],'row':1,'column':0},
                erl2context=self.erl2context)
        else:
            self.sensors['temperature'] = Erl2Input(
                sensorType='temperature',
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                correctionLoc={'parent':self.__frames['Temp'][0][2],'row':1,'column':0},
                erl2context=self.erl2context)

        # readout displays for the current pH, as reported by the pico-pH
        self.sensors['pH'] = Erl2Pyro(
            sensorType='pH',
            displayLocs=[{'parent':self.__frames['Data'][1][0],'row':1,'column':0},
                         {'parent':self.__frames['pH'][0][0],'row':1,'column':0}],
            statusLocs=pHStatusLocs,
            correctionLoc={'parent':self.__frames['pH'][0][2],'row':1,'column':0},
            tempSensor=self.sensors['temperature'],
            erl2context=self.erl2context)

        # readout displays for the current DO, as reported by the pico-o2
        self.sensors['DO'] = Erl2Pyro(
            sensorType='DO',
            displayLocs=[{'parent':self.__frames['Data'][2][0],'row':1,'column':0},
                         {'parent':self.__frames['DO'][0][0],'row':1,'column':0}],
            statusLocs=doStatusLocs,
            correctionLoc={'parent':self.__frames['DO'][0][2],'row':1,'column':0},
            tempSensor=self.sensors['temperature'],
            erl2context=self.erl2context)

        # readout displays for the current Air MFC flow rate
        self.sensors['mfc.air'] = Erl2Input(
            sensorType='mfc.air',
            displayLocs=[{'parent':self.__frames['Data'][1][1],'row':1,'column':0},
                         {'parent':self.__frames['pH'][0][1],'row':1,'column':0},
                         {'parent':self.__frames['Data'][2][1],'row':1,'column':0},
                         {'parent':self.__frames['DO'][0][1],'row':1,'column':0}],
            statusLocs=airMfcStatusLocs,
            label='Air',
            erl2context=self.erl2context)

        # readout displays for the current CO2 MFC flow rate
        self.sensors['mfc.co2'] = Erl2Input(
            sensorType='mfc.co2',
            displayLocs=[{'parent':self.__frames['Data'][1][1],'row':3,'column':0},
                         {'parent':self.__frames['pH'][0][1],'row':3,'column':0}],
            statusLocs=co2MfcStatusLocs,
            label=u'CO\u2082',
            erl2context=self.erl2context)

        # readout displays for the current N2 MFC flow rate
        self.sensors['mfc.n2'] = Erl2Input(
            sensorType='mfc.n2',
            displayLocs=[{'parent':self.__frames['Data'][2][1],'row':3,'column':0},
                         {'parent':self.__frames['DO'][0][1],'row':3,'column':0}],
            statusLocs=n2MfcStatusLocs,
            label=u'N\u2082',
            erl2context=self.erl2context)

        # readout and control widgets for the Heater relay
        self.controls['heater'] = Erl2Heater(
            displayLocs=[{'parent':self.__frames['Data'][0][1],'row':0,'column':0},
                         {'parent':self.__frames['Temp'][0][1],'row':0,'column':0}],
            buttonLoc={'parent':self.__frames['Temp'][1][1],'row':1,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the Chiller solenoid
        self.controls['chiller'] = Erl2Chiller(
            displayLocs=[{'parent':self.__frames['Data'][0][1],'row':1,'column':0},
                         {'parent':self.__frames['Temp'][0][1],'row':1,'column':0}],
            buttonLoc={'parent':self.__frames['Temp'][1][1],'row':2,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the Air MFC
        self.controls['mfc.air'] = Erl2Mfc(
            controlType='mfc.air',
            settingDisplayLocs=[{'parent':self.__frames['Data'][1][1],'row':2,'column':0},
                                {'parent':self.__frames['pH'][0][1],'row':2,'column':0},
                                {'parent':self.__frames['Data'][2][1],'row':2,'column':0},
                                {'parent':self.__frames['DO'][0][1],'row':2,'column':0}],
            entryLoc={'parent':self.__frames['pH'][1][1],'row':1,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the CO2 MFC
        self.controls['mfc.co2'] = Erl2Mfc(
            controlType='mfc.co2',
            settingDisplayLocs=[{'parent':self.__frames['Data'][1][1],'row':4,'column':0},
                                {'parent':self.__frames['pH'][0][1],'row':4,'column':0}],
            entryLoc={'parent':self.__frames['pH'][1][1],'row':2,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the N2 MFC
        self.controls['mfc.n2'] = Erl2Mfc(
            controlType='mfc.n2',
            settingDisplayLocs=[{'parent':self.__frames['Data'][2][1],'row':4,'column':0},
                                {'parent':self.__frames['DO'][0][1],'row':4,'column':0}],
            entryLoc={'parent':self.__frames['DO'][1][1],'row':1,'column':0},
            erl2context=self.erl2context)

        # the logic that implements the overarching temperature subsystem (and its controls)
        self.systems['temperature'] = Erl2SubSystem(
            subSystemType='temperature',
            logic='hysteresis',
            radioLoc={'parent':self.__frames['Temp'][1][0],'row':0,'column':0},
            staticSetpointLoc={'parent':self.__frames['Temp'][1][2],'row':1,'column':0},
            hysteresisLoc={'parent':self.__frames['Temp'][1][2],'row':2,'column':0},
            dynamicSetpointsLoc={'parent':self.__frames['Temp'][2][0],'row':1,'column':0},

            setpointDisplayLocs=[{'parent':self.__frames['Data'][0][0],'row':3,'column':0},
                                 {'parent':self.__frames['Temp'][0][0],'row':3,'column':0}],
            modeDisplayLocs=[{'parent':self.__frames['Data'][0][0],'row':4,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':4,'column':0}],
            plotDisplayLoc={'parent':self.__frames['Data'][0][2],'row':0,'column':0},
            statsDisplayLoc={'parent':self.__frames['Data'][0][3],'row':0,'column':0},

            sensors={'temperature':self.sensors['temperature']},
            toggles={'to.raise':self.controls['heater'],
                     'to.lower':self.controls['chiller']},
            erl2context=self.erl2context)

        # the logic that implements the overarching pH subsystem (and its controls)
        self.systems['pH'] = Erl2SubSystem(
            subSystemType='pH',
            logic='PID',
            radioLoc={'parent':self.__frames['pH'][1][0],'row':0,'column':0},
            staticSetpointLoc={'parent':self.__frames['pH'][1][2],'row':1,'column':0},
            dynamicSetpointsLoc={'parent':self.__frames['pH'][2][0],'row':1,'column':0},

            setpointDisplayLocs=[{'parent':self.__frames['Data'][1][0],'row':3,'column':0},
                                 {'parent':self.__frames['pH'][0][0],'row':3,'column':0}],
            modeDisplayLocs=[{'parent':self.__frames['Data'][1][0],'row':4,'column':0},
                             {'parent':self.__frames['pH'][0][0],'row':4,'column':0}],
            plotDisplayLoc={'parent':self.__frames['Data'][1][2],'row':0,'column':0},
            statsDisplayLoc={'parent':self.__frames['Data'][1][3],'row':0,'column':0},

            sensors={'pH':self.sensors['pH']},
            MFCs={'mfc.air':self.controls['mfc.air'],
                  'mfc.co2':self.controls['mfc.co2']},
            erl2context=self.erl2context)

        # the logic that implements the overarching DO subsystem (and its controls)
        self.systems['DO'] = Erl2SubSystem(
            subSystemType='DO',
            logic='PID',
            radioLoc={'parent':self.__frames['DO'][1][0],'row':0,'column':0},
            staticSetpointLoc={'parent':self.__frames['DO'][1][2],'row':1,'column':0},
            dynamicSetpointsLoc={'parent':self.__frames['DO'][2][0],'row':1,'column':0},

            setpointDisplayLocs=[{'parent':self.__frames['Data'][2][0],'row':3,'column':0},
                                 {'parent':self.__frames['DO'][0][0],'row':3,'column':0}],
            modeDisplayLocs=[{'parent':self.__frames['Data'][2][0],'row':4,'column':0},
                             {'parent':self.__frames['DO'][0][0],'row':4,'column':0}],
            plotDisplayLoc={'parent':self.__frames['Data'][2][2],'row':0,'column':0},
            statsDisplayLoc={'parent':self.__frames['Data'][2][3],'row':0,'column':0},

            sensors={'DO':self.sensors['DO']},
            MFCs={'mfc.air':self.controls['mfc.air'],
                  'mfc.n2':self.controls['mfc.n2']},
            erl2context=self.erl2context)

        # the logic that enables tank networking, if enabled
        if self.erl2context['conf']['network']['tankNetwork']:
            self.network = Erl2Network(ipLocs=ipLocs,
                                       macLocs=macLocs,
                                       statusLocs=netStatusLocs,
                                      )

        # standardized labels for some Temp, pH and DO frames
        for name in ['Temp', 'pH', 'DO']:
            ttk.Label(self.__frames[name][0][2], text=name+' Correction', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][1], text='Manual Controls', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][2], text='Auto Controls', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][2][0], text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][0][3], text='Error Report', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][0][3], text=dummyError, font='Arial 14', wraplength=250
                #, relief='solid', borderwidth=1
                ).grid(row=1, column=0, sticky='nw')

        # label is different for virtual sensor
        tempLabel = u'Temperature (\u00B0C)'
        if self.erl2context['conf']['virtualtemp']['enabled']:
            tempLabel = u'Virtual Temp (\u00B0C)'

        # temperature labels
        for f in [self.__frames['Data'][0][0], self.__frames['Temp'][0][0]]:
            ttk.Label(f, text=tempLabel, font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')

        # pH labels
        for f in [self.__frames['Data'][1][0], self.__frames['pH'][0][0]]:
            ttk.Label(f, text='pH (Total Scale)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
        for f in [self.__frames['Data'][1][1], self.__frames['pH'][0][1]]:
            ttk.Label(f, text=u'Gas Flow (mL min\u207B\u00B9)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')

        # DO labels
        for f in [self.__frames['Data'][2][0], self.__frames['DO'][0][0]]:
            ttk.Label(f, text=u'DO (\u00B5mol L\u207B\u00B9)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
        for f in [self.__frames['Data'][2][1], self.__frames['DO'][0][1]]:
            ttk.Label(f, text=u'Gas Flow (mL min\u207B\u00B9)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')

        ## placeholder stats
        #ttk.Label(self.__frames['Data'][0][3], text='25.0', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][0][3], text='0.10', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=1, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][0][3], text='0.10', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=2, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][1][3], text='7.80', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][1][3], text='0.010', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=1, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][1][3], text='0.010', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=2, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][2][3], text='300', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][2][3], text='1.0', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=1, column=1, padx='2 0', sticky='ne')
        #ttk.Label(self.__frames['Data'][2][3], text='1.0', font='Arial 14 bold', foreground='#A93226'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=2, column=1, padx='2 0', sticky='ne')

        # frames for stats
        for row in range(3):

        #    ttk.Label(self.__frames['Data'][row][3], text='Mean:', font='Arial 14'
        #        #, relief='solid', borderwidth=1
        #        ).grid(row=0, column=0, sticky='nw')
        #    ttk.Label(self.__frames['Data'][row][3], text='Stdev:', font='Arial 14'
        #        #, relief='solid', borderwidth=1
        #        ).grid(row=1, column=0, sticky='nw')
        #    ttk.Label(self.__frames['Data'][row][3], text='Target dev:', font='Arial 14'
        #        #, relief='solid', borderwidth=1
        #        ).grid(row=2, column=0, sticky='nw')

            # weighting
            self.__frames['Data'][row][3].columnconfigure(0,weight=0)
            self.__frames['Data'][row][3].columnconfigure(1,weight=1)

        # misc spacing/weighting
        for f in [self.__frames['Data'][0][0],
                  self.__frames['Data'][1][0],
                  self.__frames['Data'][2][0],
                  self.__frames['Temp'][0][0],
                  self.__frames['pH'][0][0],
                  self.__frames['DO'][0][0],
                 ]:
            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=1)

        # start up the timing loop to update the system log
        self.updateLog()

    def updateLog(self):

        # record the current timestamp
        currentTime = dt.now(tz=tz.utc)

        # if we've passed the next file-writing interval time, write it
        if self.__nextFileTime is not None and currentTime.timestamp() > self.__nextFileTime:

            # send the new sensor data to the log (in dictionary form)
            if self.__systemLog is not None:

                # create a composite 'measurement' made up of sensor and control data
                m = {'Timestamp.UTC': currentTime.strftime(self.erl2context['conf']['system']['dtFormat']),
                     'Timestamp.Local': currentTime.astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat'])}

                # sensor / temperature : 'temp.degC'
                if ('temperature' in self.sensors
                    and hasattr(self.sensors['temperature'], 'value')
                    and 'temp.degC' in self.sensors['temperature'].value):
                    m['temperature'] = self.sensors['temperature'].value['temp.degC']
                else:
                    m['temperature'] = None

                # sensor / pH : 'pH'
                if ('pH' in self.sensors
                    and hasattr(self.sensors['pH'], 'value')
                    and 'pH' in self.sensors['pH'].value):
                    m['pH'] = self.sensors['pH'].value['pH']
                else:
                    m['pH'] = None

                # sensor / DO : 'uM'
                if ('DO' in self.sensors
                    and hasattr(self.sensors['DO'], 'value')
                    and 'uM' in self.sensors['DO'].value):
                    m['DO'] = self.sensors['DO'].value['uM']
                else:
                    m['DO'] = None

                # control / chiller : 'On (seconds)'
                if ('chiller' in self.controls
                    and hasattr(self.controls['chiller'], 'value')
                    and 'On (seconds)' in self.controls['chiller'].value):
                    m['chiller'] = self.controls['chiller'].value['On (seconds)']
                else:
                    m['chiller'] = None

                # control / heater : 'On (seconds)'
                if ('heater' in self.controls
                    and hasattr(self.controls['heater'], 'value')
                    and 'On (seconds)' in self.controls['heater'].value):
                    m['heater'] = self.controls['heater'].value['On (seconds)']
                else:
                    m['heater'] = None

                # control / mfc.air : 'Average Flow Setting'
                if ('mfc.air' in self.controls
                    and hasattr(self.controls['mfc.air'], 'value')
                    and 'Average Flow Setting' in self.controls['mfc.air'].value):
                    m['mfc.air'] = self.controls['mfc.air'].value['Average Flow Setting']
                else:
                    m['mfc.air'] = None

                # control / mfc.co2 : 'Average Flow Setting'
                if ('mfc.co2' in self.controls
                    and hasattr(self.controls['mfc.co2'], 'value')
                    and 'Average Flow Setting' in self.controls['mfc.co2'].value):
                    m['mfc.co2'] = self.controls['mfc.co2'].value['Average Flow Setting']
                else:
                    m['mfc.co2'] = None

                # control / mfc.n2 : 'Average Flow Setting'
                if ('mfc.n2' in self.controls
                    and hasattr(self.controls['mfc.n2'], 'value')
                    and 'Average Flow Setting' in self.controls['mfc.n2'].value):
                    m['mfc.n2'] = self.controls['mfc.n2'].value['Average Flow Setting']
                else:
                    m['mfc.n2'] = None

                # write out the composite log record for the tank
                self.__systemLog.writeData(m)

        # if the next file-writing interval time is empty or in the past, update it
        if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
            self.__nextFileTime = Erl2Log.nextIntervalTime(currentTime, self.erl2context['conf']['system']['loggingFrequency'])

        # update the log again after waiting an appropriate number of milliseconds
        delay = int((self.__nextFileTime - currentTime.timestamp())*1000)
        self.__frames['Settings'][0][1].after(delay, self.updateLog)

    # a method to call whenever we detect a tab change
    def changeTabs(self, event):

        id = self.__mainTabs.select()
        p = self.__mainTabs.tab(id, "text")
        #print (f"{self.__class__.__name__}: Debug: tab changed to [{p}]")

        # set focus to an arbitrary frame to avoid seeing focus on entry or button widgets
        self.__frames[p][0][0].focus()

        # explicitly deselect the sensor's firstEntry field
        for s in self.sensors.values():
            if s.firstEntry is not None:
                s.firstEntry.widget.select_clear()

        #for row in range(3):
        #   print (f"{self.__class__.__name__}: Debug: changeTabs({p}): frame width is [{self.__frames['Data'][row][2].winfo_width()}], frame height is [{self.__frames['Data'][row][2].winfo_height()}]")

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
        self.__parent.attributes('-fullscreen', bool(val))

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
            self.__systemLog.writeMessage('Erl2Tank system restart requested by GUI user')

            # terminate the current system and start it up again
            self.__restart = True
            self.gracefulExit()

    # shut down the App
    def exitApp(self, event=None):

        # ask for confirmation
        if mb.askyesno('Shut Down Confirmation','Are you sure you want to shut down the ERL2 App now?'):

            # mention this in the log
            self.__systemLog.writeMessage('Erl2Tank system exit requested by GUI user')

            # terminate the system
            self.gracefulExit()

    # atexit.register() handler
    def atexitHandler(self):

        # make note in the logs if this event wasn't triggered by some other trapped signal
        if not self.erl2context['conf']['system']['shutdown']:
            self.__systemLog.writeMessage('Erl2Tank atexit handler triggered for App shutdown')

        # proceed with app termination
        self.gracefulExit()

    # signal handler
    def signalHandler(self, *args):

        # add a log entry to note any signals that were trapped
        if len(args) > 0:
            self.__systemLog.writeMessage(f"Erl2Tank trapped signal [{signal.Signals(args[0]).name}], exiting")

        # proceed with app termination
        self.gracefulExit()

    # for a graceful shutdown
    def gracefulExit(self, *args):

        # avoid repeated calls to this handler
        if self.erl2context['conf']['system']['shutdown']:
            return
        self.erl2context['conf']['system']['shutdown'] = True

        # set any controls to zero
        if hasattr(self, 'controls'):
            for c in self.controls.values():
                c.setControl(0,force=True)
            #self.__systemLog.writeMessage(f"Erl2Tank Debug: zeroed out [{len(self.controls)}] controls")

        # terminate subthreads in network module
        if self.network is not None:
            self.network.atexitHandler()

        # terminate the current system and start it up again (if asked to do so)
        if self.__restart:
            python = sys.executable
            os.execl(python, python, * sys.argv)

        # otherwise, just terminate the system
        else:
            #self.__parent.destroy() # this was leaving some .after() callbacks hanging
            tk.Tk.quit(self.__parent)

def main():

    root = tk.Tk()
    #root.attributes('-fullscreen', True)
    #root.attributes('-topmost', True)
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    tank = Erl2Tank(root)
    tank.setFullscreen()

    # set things up for graceful termination
    atexit.register(tank.atexitHandler)
    signal.signal(signal.SIGHUP,tank.signalHandler)
    signal.signal(signal.SIGINT,tank.signalHandler)
    signal.signal(signal.SIGTERM,tank.signalHandler)

    root.mainloop()

if __name__ == "__main__": main()

