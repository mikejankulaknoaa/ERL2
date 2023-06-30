#! /usr/bin/python3

from os import execl
from sys import argv,executable
import tkinter as tk
from tkinter import ttk
from Erl2Chiller import Erl2Chiller
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Heater import Erl2Heater
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2pH import Erl2pH
from Erl2SubSystem import Erl2SubSystem
from Erl2Temperature import Erl2Temperature
from Erl2VirtualTemp import Erl2VirtualTemp

class Erl2Tank:

    def __init__(self, parent, erl2conf=None, img=None):
        self.__parent = parent
        self.erl2conf = erl2conf
        self.img = img

        # read in the system configuration file if needed
        if self.erl2conf is None:
            self.erl2conf = Erl2Config()
            #if 'tank' in self.erl2conf.sections() and 'id' in self.erl2conf['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2conf['tank']['id']}]")

        # start a system log
        self.__systemLog = Erl2Log(logType='system', logName='Erl2Tank', erl2conf=self.erl2conf)
        self.__systemLog.writeMessage('Erl2Tank system startup')

        # if necessary, create an object to hold/remember image objects
        if self.img is None:
            self.img = Erl2Image(erl2conf=self.erl2conf)

        # load some images that will be useful later on
        self.img.addImage('checkOff','checkbox-off-25.png')
        self.img.addImage('checkOn','checkbox-on-25.png')
        self.img.addImage('reload','reload-25.png')
        self.img.addImage('shutdown','shutdown-25.png')

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

        # we have a checkbox for changing between fullscreen and back
        self.__fullscreenVar = tk.IntVar()
        self.__fullscreenVar.set(1)

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
                          erl2conf=self.erl2conf,
                          img=self.img)

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
                    elif (p in ['Temp','pH','DO'] and r==1 and c==0):
                        self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                        self.__frames[p][r][c].grid(row=r, column=c, columnspan=2, padx='2', pady='2', sticky='nesw')
                    elif (p in ['Temp','pH','DO'] and r==2 and c==0):
                        self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                        self.__frames[p][r][c].grid(row=r, column=c, columnspan=4, padx='2', pady='2', sticky='nesw')
                    elif (p in ['Temp','pH','DO'] and (r,c) in [(1,1),(1,3),(2,1),(2,2),(2,3)]):
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
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2conf['system']['version'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Tank Id:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2conf['tank']['id'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Tank Location:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2conf['tank']['location'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Log Directory:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        if self.erl2conf['system']['disableFileLogging']:
            txt = '<disabled>'
        else:
            txt = self.erl2conf['system']['logDir']
        ttk.Label(self.__frames['Settings'][0][1], text=txt, font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Logging Frequency:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        if (    self.erl2conf['temperature']['loggingFrequency']
             == self.erl2conf['pH']['loggingFrequency']
             == self.erl2conf['heater']['loggingFrequency']
             == self.erl2conf['chiller']['loggingFrequency']):
            txt = str(self.erl2conf['temperature']['loggingFrequency']) + ' seconds'
        else:
            txt = (  'Temperature: ' + self.erl2conf['temperature']['loggingFrequency'] + 'seconds; '
                   + 'pH: '          + self.erl2conf['pH'         ]['loggingFrequency'] + 'seconds; '
                   + 'Heater: '      + self.erl2conf['heater'     ]['loggingFrequency'] + 'seconds; '
                   + 'Chiller: '     + self.erl2conf['chiller'    ]['loggingFrequency'] + 'seconds'
                  )
        ttk.Label(self.__frames['Settings'][0][1], text=txt, font=fontright, wraplength=300
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='System Startup:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2conf['system']['startup'].astimezone(self.erl2conf['system']['timezone']).strftime(self.erl2conf['system']['dtFormat']), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='System Timezone:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=str(self.erl2conf['system']['timezone']), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Temperature Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        tempStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        if self.erl2conf['virtualtemp']['enabled']:
            r += 1
            ttk.Label(self.__frames['Settings'][0][1], text='-- using Virtual Temperature --', font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='pH Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        pHStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        # dummy row
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
        fullscreenFrame = ttk.Frame(self.__frames['Settings'][0][0], padding='2 2', relief='solid', borderwidth=0)
        fullscreenFrame.grid(row=1, column=0, padx='2', pady='2', sticky='nwse')
        fullscreenCheckbutton = tk.Checkbutton(fullscreenFrame,
                                               indicatoron=0,
                                               image=self.img['checkOff'],
                                               selectimage=self.img['checkOn'],
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
        ttk.Label(fullscreenFrame, text='Fullscreen', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=1, padx='2 2', sticky='w')

        fullscreenFrame.rowconfigure(0,weight=1)
        fullscreenFrame.columnconfigure(0,weight=0)
        fullscreenFrame.columnconfigure(1,weight=1)

        # restart the app
        restartFrame = ttk.Frame(self.__frames['Settings'][1][0], padding='2 2', relief='solid', borderwidth=0)
        restartFrame.grid(row=1, column=0, padx='2', pady='2', sticky='nwse')
        restartButton = tk.Button(restartFrame,
                                  image=self.img['reload'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  activebackground='#DBDBDB',
                                  command=self.restartPrototype)
        restartButton.grid(row=0, column=0, padx='2 2', sticky='w')
        #restartButton.image = self.img['reload']
        ttk.Label(restartFrame, text='Restart ERL2', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=1, padx='2 2', sticky='w')

        restartFrame.rowconfigure(0,weight=1)
        restartFrame.columnconfigure(0,weight=0)
        restartFrame.columnconfigure(1,weight=1)

        # kill the app completely with this shutdown button
        exitFrame = ttk.Frame(self.__frames['Settings'][1][0], padding='2 2', relief='solid', borderwidth=0)
        exitFrame.grid(row=2, column=0, padx='2', pady='2', sticky='nwse')
        exitButton = tk.Button(exitFrame,
                               image=self.img['shutdown'],
                               height=40,
                               width=40,
                               bd=0,
                               highlightthickness=0,
                               activebackground='#DBDBDB',
                               command=self.exitPrototype)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        #exitButton.image = self.img['shutdown']
        ttk.Label(exitFrame, text='Shut down ERL2', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=1, padx='2 2', sticky='w')

        exitFrame.rowconfigure(0,weight=1)
        exitFrame.columnconfigure(0,weight=0)
        exitFrame.columnconfigure(1,weight=1)

        # readout displays for the current temperature (real or virtual)
        if self.erl2conf['virtualtemp']['enabled']:
            self.sensors['temperature'] = Erl2VirtualTemp(
                parent=self,
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                erl2conf=self.erl2conf,
                img=self.img)
        else:
            self.sensors['temperature'] = Erl2Temperature(
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                erl2conf=self.erl2conf,
                img=self.img)

        # readout and control widgets for the Heater relay
        self.controls['heater'] = Erl2Heater(
            displayLocs=[{'parent':self.__frames['Data'][0][1],'row':0,'column':0},
                         {'parent':self.__frames['Temp'][0][1],'row':0,'column':0}],
            buttonLocs=[{'parent':self.__frames['Temp'][1][2],'row':2,'column':0}],
            erl2conf=self.erl2conf,
            img=self.img)

        # readout and control widgets for the Chiller solenoid
        self.controls['chiller'] = Erl2Chiller(
            displayLocs=[{'parent':self.__frames['Data'][0][1],'row':1,'column':0},
                         {'parent':self.__frames['Temp'][0][1],'row':1,'column':0}],
            buttonLocs=[{'parent':self.__frames['Temp'][1][2],'row':3,'column':0}],
            erl2conf=self.erl2conf,
            img=self.img)

        # and the logic that implements the overarching temperature subsystem (and its controls)
        self.systems['temperature'] = Erl2SubSystem(
            radioLoc={'parent':self.__frames['Temp'][1][0],'row':0,'column':0},
            staticLoc={'parent':self.__frames['Temp'][1][2],'row':1,'column':0},
            offsetLoc={'parent':self.__frames['Temp'][0][2],'row':1,'column':0},
            dynamicLoc={'parent':self.__frames['Temp'][2][0],'row':1,'column':0},

            setpointLocs=[{'parent':self.__frames['Data'][0][0],'row':3,'column':0},
                          {'parent':self.__frames['Temp'][0][0],'row':3,'column':0}],
            modeLocs=[{'parent':self.__frames['Data'][0][0],'row':4,'column':0},
                      {'parent':self.__frames['Temp'][0][0],'row':4,'column':0}],

            sensors={'temperature':self.sensors['temperature']},
            controls={'heater':self.controls['heater'],
                      'chiller':self.controls['chiller']},
            erl2conf=self.erl2conf,
            img=self.img)

        # label is different for virtual sensor
        tempLabel = u'Temperature (\u00B0C)'
        if self.erl2conf['virtualtemp']['enabled']:
            tempLabel = u'Virtual Temp (\u00B0C)'

        # temperature labels
        for f in [self.__frames['Data'][0][0], self.__frames['Temp'][0][0]]:
            ttk.Label(f, text=tempLabel, font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')

        ttk.Label(self.__frames['Temp'][0][2], text='Temperature Offset', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['Temp'][1][2], text='Auto Static Setpoint', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['Temp'][2][0], text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['Temp'][0][3], text='Error Report', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['Temp'][0][3], text=dummyError, font='Arial 14', wraplength=300
            #, relief='solid', borderwidth=1
            ).grid(row=1, column=0, sticky='nw')

        # readout displays for the current pH, as reported by the pico-pH
        self.sensors['pH'] = Erl2pH(
            displayLocs=[{'parent':self.__frames['Data'][1][0],'row':1,'column':0},
                         {'parent':self.__frames['pH'][0][0],'row':1,'column':0}],
            statusLocs=pHStatusLocs,
            port='/dev/ttyAMA1',
            tempSensor=self.sensors['temperature'],
            erl2conf=self.erl2conf)

        # temperature label spacing/weighting
        for f in [self.__frames['Data'][0][0], self.__frames['Temp'][0][0]]:
            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # pH labels
        for f in [self.__frames['Data'][1][0], self.__frames['pH'][0][0]]:
            ttk.Label(f, text='pH (Total Scale)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(f, text='7.80', font='Arial 20', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Auto static pH mode', font='Arial 10 bold italic', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

        ttk.Label(self.__frames['pH'][0][2], text='pH Offset', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['pH'][1][2], text='Auto Static Setpoint', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['pH'][2][0], text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['pH'][0][3], text='Error Report', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['pH'][0][3], text=dummyError, font='Arial 14', wraplength=300
            #, relief='solid', borderwidth=1
            ).grid(row=1, column=0, sticky='nw')

        # pH label spacing/weighting
        for f in [self.__frames['Data'][1][0], self.__frames['pH'][0][0]]:
            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # add placeholder(s) for dissolved oxygen
        for f in [self.__frames['Data'][2][0], self.__frames['DO'][0][0]]:
            o2sf = ttk.Frame(f, padding='0 0', relief='solid', borderwidth=0)
            o2sf.grid(row=1, column=0, padx='2', pady='0', sticky='nesw')
            o2s = ttk.Label(o2sf, text='705', font='Arial 40 bold', foreground='#A93226')
            o2s.grid(row=0, column=0, sticky='n')

            # dissolved oxygen labels
            ttk.Label(f, text=u'DO (\u00B5mol L\u207B\u00B9)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(f, text='700', font='Arial 20', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Off', font='Arial 10 bold italic', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        ttk.Label(self.__frames['DO'][0][2], text='DO Offset', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['DO'][1][2], text='Auto Static Setpoint', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['DO'][2][0], text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['DO'][0][3], text='Error Report', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(self.__frames['DO'][0][3], text=dummyError, font='Arial 14', wraplength=300
            #, relief='solid', borderwidth=1
            ).grid(row=1, column=0, sticky='nw')

    # a method to call whenever we detect a tab change
    def changeTabs(self, event):

        id = self.__mainTabs.select()
        p = self.__mainTabs.tab(id, "text")
        #print (f"{self.__class__.__name__}: Debug: tab changed to [{p}]")

        # set focus to an arbitrary frame to avoid seeing focus on entry or button widgets
        #self.__frames[p][1][0].focus()

    # temporary: an exit button for convenience while coding
    def setFullscreen(self):

        if self.__fullscreenVar.get() == 1:
            self.__parent.attributes('-fullscreen', True)
        else:
            self.__parent.attributes('-fullscreen', False)

    # restart the prototype
    def restartPrototype(self):

        # mention this in the log
        self.__systemLog.writeMessage('Erl2Tank system restart requested by GUI user')

        # terminate the current system and start it up again
        python = executable
        execl(python, python, * argv)

    # an exit button for convenience while coding
    def exitPrototype(self):

        # mention this in the log
        self.__systemLog.writeMessage('Erl2Tank system exit requested by GUI user')

        # terminate the system
        self.__parent.destroy()

def main():

    root = tk.Tk()
    #root.configure(bg='grey')
    root.attributes('-fullscreen', True)
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    tank = Erl2Tank(root)
    root.mainloop()

if __name__ == "__main__": main()

