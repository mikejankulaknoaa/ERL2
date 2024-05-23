from datetime import datetime as dt
from datetime import timezone as tz
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Chiller import Erl2Chiller
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Heater import Erl2Heater
from Erl2Input import Erl2Input
from Erl2Log import Erl2Log
from Erl2Mfc import Erl2Mfc
from Erl2Network import Erl2Network
from Erl2Pyro import Erl2Pyro
from Erl2SerialTemp import Erl2SerialTemp
from Erl2State import Erl2State
from Erl2SubSystem import Erl2SubSystem
from Erl2VirtualTemp import Erl2VirtualTemp
from Erl2Useful import nextIntervalTime

class Erl2Tank:

    def __init__(self, erl2context={}):
        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # pop up a warning message if called directly
        if 'startup' not in self.erl2context:
            if not mb.askyesno('Warning',
                               'You have started up the Erl2Tank module directly,'
                               ' which is deprecated in favor of using the newer'
                               ' ErlStartup module. Are you sure you wish to do this?',
                               parent=self.erl2context['root']):
                sys.exit()

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # read these useful parameters from Erl2Config
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__serialTemp = self.erl2context['conf']['temperature']['serialPort']
        self.__virtualTemp = self.erl2context['conf']['virtualtemp']['enabled']
        self.__systemFrequency = self.erl2context['conf']['system']['loggingFrequency']

        # this parameter is written (to share w/controller) but never read
        self.erl2context['state'].set([('virtualtemp','enabled',self.__virtualTemp)])

        # start a system log
        self.__systemLog = Erl2Log(logType='device', logName='Erl2Tank', erl2context=self.erl2context)

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # stylistic stuff
        s = ttk.Style()
        s.configure('TNotebook',tabposition='nw',borderwidth=1,relief='solid')
        s.configure('TNotebook.Tab',font='Arial 16 italic',borderwidth=1,relief='solid',padding='3 3',tabmargins='2 2 2 0',width=8)

        # these dicts will hold the objects in this module
        self.__tabs = {}
        self.__frames = {}
        self.sensors = {}
        self.controls = {}
        self.subsystems = {}

        # remember if network module is active
        #self.network = None

        # the top-level element is a notebook (tabbed screens)
        self.__mainTabs = ttk.Notebook(self.erl2context['root'],padding='5 5 5 2')
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
            self.__mainTabs.add(self.__tabs[p],text=p,padding='0')

            # add frames to allWidgets array for widgetless modules add use .after() methods
            self.erl2context['conf']['system']['allWidgets'].append(self.__tabs[p])
            #print (f"{self.__class__.__name__}: Debug: tabNames[{p}]: allWidgets length [{len(self.erl2context['conf']['system']['allWidgets'])}]")

        # add a clock widget in the upper right corner
        clock = Erl2Clock(clockLoc={'parent':self.erl2context['root'],'row':0,'column':0},
                          erl2context=self.erl2context)

        # quickly create 3x4 grids of frames in all tabs except Settings
        for p in [x for x in self.__tabNames if x != 'Settings']:
            self.__frames[p] = {}
            for r in range(3):
                self.__frames[p][r] = {}
                for c in range(4):

                    # some pages have frames that span more than one row or column
                    #if (p in ['Temp','pH','DO'] and r==0 and c==3):
                    #    self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                    #    self.__frames[p][r][c].grid(row=r, column=c, rowspan=2, padx='2', pady='2', sticky='nesw')
                    ##elif (p in ['Temp','pH','DO'] and r==1 and c==0):
                    ##    self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                    ##    self.__frames[p][r][c].grid(row=r, column=c, columnspan=2, padx='2', pady='2', sticky='nesw')
                    #elif (p in ['Temp','pH','DO'] and r==2 and c==0):
                    if (p in ['Temp','pH','DO'] and r==2 and c==0):
                        self.__frames[p][r][c] = ttk.Frame(self.__tabs[p], padding='2', relief='solid', borderwidth=1)
                        self.__frames[p][r][c].grid(row=r, column=c, columnspan=4, padx='2', pady='2', sticky='nesw')
                    #elif (p in ['Temp','pH','DO'] and (r,c) in [(1,1),(1,3),(2,1),(2,2),(2,3)]):
                    #elif (p in ['Temp','pH','DO'] and (r,c) in [(1,3),(2,1),(2,2),(2,3)]):
                    elif (p in ['Temp','pH','DO'] and (r,c) in [(2,1),(2,2),(2,3)]):
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
        dummyError += ' Ut enim ad minim'
        #dummyError += ' veniam, quis nostrud exercitation ullamco'
        #dummyError += ' laboris nisi ut aliquip ex ea commodo consequat.'
        #dummyError += ' Duis aute irure dolor in reprehenderit in voluptate velit'
        #dummyError += ' esse cillum'
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
        ttk.Label(self.__frames['Settings'][0][1], text=self.erl2context['conf']['system']['startup'].astimezone(self.__timezone).strftime(self.__dtFormat), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='System Timezone:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(self.__frames['Settings'][0][1], text=str(self.__timezone), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(self.__frames['Settings'][0][1], text='Temperature Last Read:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        tempStatusLocs=[{'parent':self.__frames['Settings'][0][1],'row':r,'column':1}]

        if self.__virtualTemp:
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
        if self.erl2context['conf']['network']['enabled']:
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

        # these controls are defined in the startup module
        if ('startup' in self.erl2context):

            # add a control to set / unset fullscreen mode
            r = 1
            self.erl2context['startup'].createFullscreenWidget(widgetLoc={'parent':self.__frames['Settings'][0][0],'row':r})

            # add a control to enable / disable the Erl2NumPad popups
            r += 1
            self.erl2context['startup'].createNumPadWidget(widgetLoc={'parent':self.__frames['Settings'][0][0],'row':r})

            # add a control to restart the app
            r = 1
            self.erl2context['startup'].createRestartWidget(widgetLoc={'parent':self.__frames['Settings'][1][0],'row':r})

            # kill the app completely with this shutdown button
            r += 1
            self.erl2context['startup'].createExitWidget(widgetLoc={'parent':self.__frames['Settings'][1][0],'row':r})

        # readout displays for the current temperature (virtual, serial, or milliAmps/volts)
        if self.__virtualTemp:
            self.sensors['temperature'] = Erl2VirtualTemp(
                erl2Parent=self,
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                correctionLoc={'parent':self.__frames['Temp'][0][3],'row':1,'column':0},
                erl2context=self.erl2context)
        elif self.__serialTemp is not None:
            self.sensors['temperature'] = Erl2SerialTemp(
                sensorType='temperature',
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                correctionLoc={'parent':self.__frames['Temp'][0][3],'row':1,'column':0},
                erl2context=self.erl2context)
        else:
            self.sensors['temperature'] = Erl2Input(
                sensorType='temperature',
                displayLocs=[{'parent':self.__frames['Data'][0][0],'row':1,'column':0},
                             {'parent':self.__frames['Temp'][0][0],'row':1,'column':0}],
                statusLocs=tempStatusLocs,
                correctionLoc={'parent':self.__frames['Temp'][0][3],'row':1,'column':0},
                erl2context=self.erl2context)

        # readout displays for the current pH, as reported by the pico-pH
        self.sensors['pH'] = Erl2Pyro(
            sensorType='pH',
            displayLocs=[{'parent':self.__frames['Data'][1][0],'row':1,'column':0},
                         {'parent':self.__frames['pH'][0][0],'row':1,'column':0}],
            statusLocs=pHStatusLocs,
            correctionLoc={'parent':self.__frames['pH'][0][3],'row':1,'column':0},
            tempSensor=self.sensors['temperature'],
            erl2context=self.erl2context)

        # readout displays for the current DO, as reported by the pico-o2
        self.sensors['DO'] = Erl2Pyro(
            sensorType='DO',
            displayLocs=[{'parent':self.__frames['Data'][2][0],'row':1,'column':0},
                         {'parent':self.__frames['DO'][0][0],'row':1,'column':0}],
            statusLocs=doStatusLocs,
            correctionLoc={'parent':self.__frames['DO'][0][3],'row':1,'column':0},
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
            buttonLoc={'parent':self.__frames['Temp'][0][2],'row':1,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the Chiller solenoid
        self.controls['chiller'] = Erl2Chiller(
            displayLocs=[{'parent':self.__frames['Data'][0][1],'row':1,'column':0},
                         {'parent':self.__frames['Temp'][0][1],'row':1,'column':0}],
            buttonLoc={'parent':self.__frames['Temp'][0][2],'row':2,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the Air MFC
        self.controls['mfc.air'] = Erl2Mfc(
            controlType='mfc.air',
            displayLocs=[{'parent':self.__frames['Data'][1][1],'row':2,'column':0},
                         {'parent':self.__frames['pH'][0][1],'row':2,'column':0},
                         {'parent':self.__frames['Data'][2][1],'row':2,'column':0},
                         {'parent':self.__frames['DO'][0][1],'row':2,'column':0}],
            entryLoc={'parent':self.__frames['pH'][0][2],'row':1,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the CO2 MFC
        self.controls['mfc.co2'] = Erl2Mfc(
            controlType='mfc.co2',
            displayLocs=[{'parent':self.__frames['Data'][1][1],'row':4,'column':0},
                         {'parent':self.__frames['pH'][0][1],'row':4,'column':0}],
            entryLoc={'parent':self.__frames['pH'][0][2],'row':2,'column':0},
            erl2context=self.erl2context)

        # readout and control widgets for the N2 MFC
        self.controls['mfc.n2'] = Erl2Mfc(
            controlType='mfc.n2',
            displayLocs=[{'parent':self.__frames['Data'][2][1],'row':4,'column':0},
                         {'parent':self.__frames['DO'][0][1],'row':4,'column':0}],
            entryLoc={'parent':self.__frames['DO'][0][2],'row':1,'column':0},
            erl2context=self.erl2context)

        # the logic that implements the overarching temperature subsystem (and its controls)
        self.subsystems['temperature'] = Erl2SubSystem(
            subSystemType='temperature',
            logic='hysteresis',
            ctrlRadioLoc={'parent':self.__frames['Temp'][1][0],'row':1,'column':0},
            modeRadioLoc={'parent':self.__frames['Temp'][1][1],'row':1,'column':0},
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
        self.subsystems['pH'] = Erl2SubSystem(
            subSystemType='pH',
            logic='PID',
            ctrlRadioLoc={'parent':self.__frames['pH'][1][0],'row':1,'column':0},
            modeRadioLoc={'parent':self.__frames['pH'][1][1],'row':1,'column':0},
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
        self.subsystems['DO'] = Erl2SubSystem(
            subSystemType='DO',
            logic='PID',
            ctrlRadioLoc={'parent':self.__frames['DO'][1][0],'row':1,'column':0},
            modeRadioLoc={'parent':self.__frames['DO'][1][1],'row':1,'column':0},
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

        # the logic that enables networking, if enabled
        if self.erl2context['conf']['network']['enabled']:

            # don't do this unless Erl2Tank was called directly
            if 'startup' in self.erl2context:
                self.erl2context['network'] = Erl2Network(systemLog=self.__systemLog,
                                                          erl2context=self.erl2context)

                # go back and add network-related widgets
                self.erl2context['network'].addWidgets(ipLocs=ipLocs,
                                                       macLocs=macLocs,
                                                       statusLocs=statusLocs)

        # standardized labels for some Temp, pH and DO frames
        for name in ['Temp', 'pH', 'DO']:
            ttk.Label(self.__frames[name][0][3], text=name+' Correction', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][0], text='Control', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][1], text='Mode', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][0][2], text='Manual Controls', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][2], text='Auto Controls', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][2][0], text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][3], text='Error Report', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__frames[name][1][3], text=dummyError, font='Arial 14', wraplength=250
                #, relief='solid', borderwidth=1
                ).grid(row=1, column=0, sticky='nw')

        # label is different for virtual sensor
        tempLabel = u'Temperature (\u00B0C)'
        if self.__virtualTemp:
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

        # frames for stats
        for row in range(3):

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
                m = {'Timestamp.UTC': currentTime.strftime(self.__dtFormat),
                     'Timestamp.Local': currentTime.astimezone(self.__timezone).strftime(self.__dtFormat)}

                # first sensors, then controls: current values and average values
                for s in self.sensors:
                    m['s.'+s], m['s.'+s+'.avg'] = self.sensors[s].reportValue(self.__systemFrequency)
                for c in self.controls:
                    m['c.'+c], m['c.'+c+'.avg'] = self.controls[c].reportValue(self.__systemFrequency)

                # write out the composite log record for the tank
                self.__systemLog.writeData(m)

        # if the next file-writing interval time is empty or in the past, update it
        if self.__nextFileTime is None or currentTime.timestamp() > self.__nextFileTime:
            self.__nextFileTime = nextIntervalTime(currentTime, self.__systemFrequency)

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

        # explicitly deselect all entry fields
        for s in list(self.sensors.values()) + list(self.controls.values()) + list(self.subsystems.values()):
            if hasattr(s, 'allEntries'):
                for e in s.allEntries:
                    e.widget.select_clear()

        #for row in range(3):
        #   print (f"{self.__class__.__name__}: Debug: changeTabs({p}): frame width is [{self.__frames['Data'][row][2].winfo_width()}], frame height is [{self.__frames['Data'][row][2].winfo_height()}]")

    # for a graceful shutdown
    def gracefulExit(self):

        # set any controls to zero
        if hasattr(self, 'controls'):
            for c in self.controls.values():
                c.setControl(0,force=True)

        # terminate subthreads in network module
        if self.erl2context['network'] is not None:
            self.erl2context['network'].atexitHandler()

def main():

    root = tk.Tk()
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    tank = Erl2Tank({'root':root})

    root.mainloop()

if __name__ == "__main__": main()

