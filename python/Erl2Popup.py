from os import makedirs,path
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2Entry import Erl2Entry
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2State import Erl2State

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

class Erl2Popup(tk.Toplevel):

    # allow only one Erl2Popup popup at a time
    erl2Popup = None
    popupType = None

    def __init__(self, erl2context={}):

        super().__init__()

        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # removes the OS window controls, but breaks logic that keeps window on top
        #self.overrideredirect(1)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']
        self.__mfcAirDec = self.erl2context['conf']['mfc.air']['displayDecimals']
        self.__mfcCO2Dec = self.erl2context['conf']['mfc.co2']['displayDecimals']
        self.__mfcN2Dec = self.erl2context['conf']['mfc.n2']['displayDecimals']
        self.__mfcAirRng = self.erl2context['conf']['mfc.air']['validRange']
        self.__mfcCO2Rng = self.erl2context['conf']['mfc.co2']['validRange']
        self.__mfcN2Rng = self.erl2context['conf']['mfc.n2']['validRange']

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load some images that will be useful later on
        for img in ['no-25.png', 'yes-25.png',
                    'radio-off-30.png', 'radio-on-30.png',
                    'radio-off-red-30.png', 'radio-on-red-30.png',
                    'radio-off-blue-30.png', 'radio-on-blue-30.png',
                    'copy-25.png', 'load-25.png', 'save-25.png']:
            self.erl2context['img'].addImage(img, img)

        # the 'Edit Tank Settings' popup needs some extra attributes
        self.__modeVar = {}
        self.__modeWidgets = {}

        # track whether a modal window is open on top of this one or not
        self.modalOpen = False

        # need a tanksettings folder in the main logging directory
        try:
            # if there's no system-level log, reroute to a debug directory
            if 'system' not in Erl2Log.logTypes:
                self.__dirName = erl2context['conf']['system']['logDir'] + '/zDebug/tanksettings'
            else:
                self.__dirName = erl2context['conf']['system']['logDir'] + '/tanksettings'

        except Exception as e:
            print (f"{self.__class__.__name__}: Error: Could not determine location of main logging directory: {e}")
            raise

        # initial directories
        if not path.isdir(erl2context['conf']['system']['logDir']):
            makedirs(erl2context['conf']['system']['logDir'])
        if not path.isdir(self.__dirName):
            makedirs(self.__dirName)

        # remember most recent filename
        self.__fileName = None

        # create a Frame to hold everything
        self.__f = ttk.Frame(self, padding='2 2', relief='flat', borderwidth=0)
        self.__f.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')

        # divide the popup frame into top (content) and bottom (buttons) sections
        displayContent = ttk.Frame(self.__f, padding='2', relief='solid', borderwidth=1)
        displayContent.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        displayButtons = ttk.Frame(self.__f, padding='0', relief='flat', borderwidth=0)
        displayButtons.grid(row=2, column=0, padx='2', pady='2', sticky='nesw')

        # label for the main content frame
        ttk.Label(displayContent, text=Erl2Popup.popupType, font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')

        # give weight to info frame
        self.__f.rowconfigure(0,weight=1)
        self.__f.rowconfigure(1,weight=0)
        self.__f.columnconfigure(0,weight=1)

        # information about this ERL2 system
        fontleft = 'Arial 14 bold'
        fontright = 'Arial 14'

        # keep track of rows in the content frame
        r = 0

        # the 'About ERL2' popup...
        if Erl2Popup.popupType == 'About ERL2':

            r += 1
            ttk.Label(displayContent, text='ERL2 Version:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['system']['version'], font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='Device Id:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['device']['id'], font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='Log Directory:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['system']['logDir'], font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='Logging Frequency:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')

            # elegant way to summarize logging frequency info
            freq = {}
            for sens in ['system']:
                if self.erl2context['conf'][sens]['loggingFrequency'] not in freq:
                    freq[self.erl2context['conf'][sens]['loggingFrequency']] = [sens]
                else:
                    freq[self.erl2context['conf'][sens]['loggingFrequency']].append(sens)
            if len(freq) == 1:
                txt = str(self.erl2context['conf']['system']['loggingFrequency']) + ' seconds'
            else:
                txt = ""
                num = 0
                for k, v in sorted(freq.items(), key=lambda item: len(item[1])):
                    num += 1
                    if num < len(freq):
                        txt += f"{', '.join(v)}: {k} seconds; "
                    else:
                        txt += f"other sensors: {k} seconds"

            ttk.Label(displayContent, text=txt, font=fontright, wraplength=300
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='System Startup:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['system']['startup'].astimezone(self.__timezone).strftime(self.__dtFormat), font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='System Timezone:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=str(self.__timezone), font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            # these items are only relevant if network is defined
            if 'network' in self.erl2context and self.erl2context['network'] is not None:
                r += 1
                ttk.Label(displayContent, text='Device Type:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                typeLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='Device Name:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                nameLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='Network Interface:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                interfaceLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='IP Address:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                ipLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='MAC Address:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                macLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='Last Network Comms:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                netStatusLocs=[{'parent':displayContent,'row':r,'column':1}]

                # add network widgets to popup
                self.erl2context['network'].addWidgets(
                                                       typeLocs=typeLocs,
                                                       nameLocs=nameLocs,
                                                       interfaceLocs=interfaceLocs,
                                                       ipLocs=ipLocs,
                                                       macLocs=macLocs,
                                                       statusLocs=netStatusLocs,
                                                       )

        # the 'Settings' popup...
        elif Erl2Popup.popupType == 'Settings':

            # these controls are defined in the startup module
            if ('startup' in self.erl2context):

                # add a control to set / unset fullscreen mode
                r += 1
                self.erl2context['startup'].createFullscreenWidget(widgetLoc={'parent':displayContent,'row':r})

                # add a control to enable / disable the Erl2NumPad popups
                r += 1
                self.erl2context['startup'].createNumPadWidget(widgetLoc={'parent':displayContent,'row':r})

        # the 'Network' popup...
        elif Erl2Popup.popupType == 'Network':

            # this item is only relevant if network is defined
            if 'network' in self.erl2context and self.erl2context['network'] is not None:

                r += 1
                childrenLocs=[{'parent':displayContent,'row':r}]

                # add network widgets to popup
                self.erl2context['network'].addWidgets(childrenLocs=childrenLocs)

        # the 'Edit Tank Settings' popup...
        elif Erl2Popup.popupType == 'Edit Tank Settings':

            r += 1
            editFrame = ttk.Frame(displayContent, padding='0', relief='flat', borderwidth=0)
            editFrame.grid(row=r, column=0, sticky='ne')

            # subframe for tanks
            tanksFrame = ttk.Frame(editFrame, padding='2', relief='solid', borderwidth=1)
            tanksFrame.grid(row=0, column=0, rowspan=3, padx='2', pady='2', sticky='nesw')
            ttk.Label(tanksFrame, text='Apply to Tanks:', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')

            # if this controller knows of any child tanks through a network connection
            if 'network' in self.erl2context and self.erl2context['network'] is not None:

                # loop through child tanks and build up a list of ids
                tankList = []
                for mac in self.erl2context['network'].sortedMacs:
                    tankList.append(self.erl2context['network'].childrenDict[mac]['id'])

                var = tk.StringVar()
                var.set(tankList)
                lbox = tk.Listbox(tanksFrame, listvariable=var, selectmode=tk.MULTIPLE, font='Arial 12')
                lbox.grid(row=1,column=0,sticky='nesw')

            # the three subSystems frames are essentially identical
            sysR = -1
            for sys in SUBSYSTEMS:
                sysR += 1
                sysF = ttk.Frame(editFrame, padding='2', relief='solid', borderwidth=1)
                sysF.grid(row=sysR, column=1, padx='2', pady='2', sticky='nesw')

                # keep track of widgets created
                self.__modeWidgets[sys] = {}

                # how many decimal places to display?
                dispDec = self.erl2context['conf'][sys]['displayDecimals']
                validRg = self.erl2context['conf'][sys]['validRange']

                # subSystem frame label
                lbl = sys
                if sys == 'temperature':
                    lbl = 'Temperature'
                ttk.Label(sysF, text=lbl + ':', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, sticky='nw')

                # mode frame
                modF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                modF.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')
                ttk.Label(modF, text='Mode', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, sticky='nw')

                # the radiobuttons themselves
                self.__modeVar[sys] = tk.IntVar()
                self.__modeWidgets[sys]['radio'] = []
                for value , text in MODEDICT.items():
                    rb = tk.Radiobutton(modF,
                                        indicatoron=0,
                                        image=self.erl2context['img']['radio-off-30.png'],
                                        selectimage=self.erl2context['img']['radio-on-30.png'],
                                        compound='left',
                                        font='Arial 16',
                                        bd=0,
                                        highlightthickness=0,
                                        activebackground='#DBDBDB',
                                        highlightcolor='#DBDBDB',
                                        highlightbackground='#DBDBDB',
                                        #bg='#DBDBDB',
                                        selectcolor='#DBDBDB',
                                        variable=self.__modeVar[sys],
                                        value=value,
                                        text=' '+text,
                                        command=lambda x=sys: self.enableWidgets(x)
                                        )
                    rb.grid(row=value+1,column=0,ipadx=2,ipady=2,sticky='w')

                    # keep a reference to all radiobutton widgets
                    self.__modeWidgets[sys]['radio'].append(rb)

                # manual controls
                manF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                manF.grid(row=1, column=1, padx='2', pady='2', sticky='nesw')
                ttk.Label(manF, text='Manual Controls', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, columnspan=2, sticky='nw')

                # manual controls look different in different subsystems
                if sys == 'temperature':

                    # temperature subSystem has toggle controls
                    self.__modeWidgets[sys]['toggle'] = []
                    self.__modeWidgets[sys]['toggle.label'] = []
                    self.__modeWidgets[sys]['toggle.value'] = []

                    # add a button widget for Heater
                    b = tk.Button(manF,
                                  image=self.erl2context['img']['radio-off-red-30.png'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  activebackground='#DBDBDB',
                                  #borderwidth=1,
                                  command=lambda x='temperature', y=0: self.setToggle(sys=x,ind=y))
                    b.grid(row=1, column=0, padx='2 2', sticky='w')

                    # this is the (text) Label shown beside the (image) button widget
                    l = ttk.Label(manF, text='Heater', font='Arial 16'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=1, column=1, padx='2 2', sticky='w')
                    l.bind('<Button-1>', lambda event, x='temperature', y=0: self.setToggle(sys=x,ind=y))

                    # keep track of control + label widgets for this control
                    self.__modeWidgets[sys]['toggle'].append(b)
                    self.__modeWidgets[sys]['toggle.label'].append(l)

                    # current setting of Heater defaults to off
                    self.__modeWidgets[sys]['toggle.value'].append(0.)

                    # add a button widget for Chiller
                    b = tk.Button(manF,
                                  image=self.erl2context['img']['radio-off-blue-30.png'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  activebackground='#DBDBDB',
                                  #borderwidth=1,
                                  command=lambda x='temperature', y=1: self.setToggle(sys=x,ind=y))
                    b.grid(row=2, column=0, padx='2 2', sticky='w')

                    # this is the (text) Label shown beside the (image) button widget
                    l = ttk.Label(manF, text='Chiller', font='Arial 16'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=2, column=1, padx='2 2', sticky='w')
                    l.bind('<Button-1>', lambda event, x='temperature', y=1: self.setToggle(sys=x,ind=y))

                    # keep track of control + label widgets for this control
                    self.__modeWidgets[sys]['toggle'].append(b)
                    self.__modeWidgets[sys]['toggle.label'].append(l)

                    # current setting of Chiller defaults to off
                    self.__modeWidgets[sys]['toggle.value'].append(0.)

                elif sys == 'pH':

                    # pH and DO subSystems have MFC (Erl2Entry) controls
                    self.__modeWidgets[sys]['manual'] = []

                    # create the entry field for manual control of the Air MFC
                    e = Erl2Entry(entryLoc={'parent':manF,'row':2,'column':1},
                                            labelLoc={'parent':manF,'row':2,'column':0},
                                            label='Air',
                                            width=5,
                                            displayDecimals=self.__mfcAirDec,
                                            validRange=self.__mfcAirRng,
                                            initValue=0.0,
                                            erl2context=self.erl2context)

                    # keep a reference to this hysteresis widget
                    self.__modeWidgets[sys]['manual'].append(e)

                    # create the entry field for manual control of the CO2 MFC
                    e = Erl2Entry(entryLoc={'parent':manF,'row':3,'column':1},
                                            labelLoc={'parent':manF,'row':3,'column':0},
                                            label=u'CO\u2082',
                                            width=5,
                                            displayDecimals=self.__mfcCO2Dec,
                                            validRange=self.__mfcCO2Rng,
                                            initValue=0.0,
                                            erl2context=self.erl2context)

                    # keep a reference to this hysteresis widget
                    self.__modeWidgets[sys]['manual'].append(e)

                elif sys == 'DO':

                    # pH and DO subSystems have MFC (Erl2Entry) controls
                    self.__modeWidgets[sys]['manual'] = []

                    # create the entry field for manual control of the N2 MFC
                    e = Erl2Entry(entryLoc={'parent':manF,'row':2,'column':1},
                                            labelLoc={'parent':manF,'row':2,'column':0},
                                            label=u'N\u2082',
                                            width=5,
                                            displayDecimals=self.__mfcN2Dec,
                                            validRange=self.__mfcN2Rng,
                                            initValue=0.0,
                                            erl2context=self.erl2context)

                    # keep a reference to this hysteresis widget
                    self.__modeWidgets[sys]['manual'].append(e)

                # auto controls
                autF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                autF.grid(row=1, column=2, padx='2', pady='2', sticky='nesw')
                ttk.Label(autF, text='Auto Controls', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, sticky='nw')

                # create the entry field for the static setpoint
                e = Erl2Entry(entryLoc={'parent':autF,'row':1,'column':1},
                                        labelLoc={'parent':autF,'row':1,'column':0},
                                        label='Static\nSetpoint',
                                        width=4,
                                        displayDecimals=dispDec,
                                        validRange=validRg,
                                        initValue=self.erl2context['conf'][sys]['setpointDefault'],
                                        erl2context=self.erl2context)

                # keep a reference to this static setpoint widget
                self.__modeWidgets[sys]['static'] = e

                # create the entry field for hysteresis (temperature only)
                if sys == 'temperature':
                    e = Erl2Entry(entryLoc={'parent':autF,'row':2,'column':1},
                                            labelLoc={'parent':autF,'row':2,'column':0},
                                            label='Hysteresis',
                                            width=4,
                                            displayDecimals=dispDec,
                                            validRange=[0.,None],
                                            initValue=self.erl2context['conf'][sys]['hysteresisDefault'],
                                            erl2context=self.erl2context)

                    # keep a reference to this hysteresis widget
                    self.__modeWidgets[sys]['hysteresis'] = e

                # auto dynamic setpoints
                dynF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                dynF.grid(row=1, column=3, padx='2', pady='2', sticky='nesw')
                ttk.Label(dynF, text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    ).grid(row=0, column=0, columnspan=24, sticky='nw')


                # add dynamic setpoint entry fields
                hourNum = 0
                self.__modeWidgets[sys]['dynamic'] = []
                #for hourVal in [0.0] * 24:
                for hourVal in self.erl2context['conf'][sys]['dynamicDefault']:

                    # lay them out in two rows, 12 boxes each
                    if hourNum < 12:
                        hourRow = 1
                        hourCol = hourNum
                        valRow = 2
                        valCol = hourNum
                        hourPady = '0 0'
                    else:
                        hourRow = 3
                        hourCol = hourNum-12
                        valRow = 4
                        valCol = hourNum-12
                        hourPady = '4 0'

                    # hour label for dynamic setpoints
                    ttk.Label(dynF, text=str(hourNum), font='Arial 12 bold'
                        #, relief='solid', borderwidth=1
                        ).grid(row=hourRow, column=hourCol, pady=hourPady, sticky='s')

                    # create the entry field for each dynamic setpoint
                    e = Erl2Entry(entryLoc={'parent':dynF,'row':valRow,'column':valCol},
                                  width=5,
                                  font='Arial 16',
                                  displayDecimals=dispDec,
                                  validRange=validRg,
                                  initValue=hourVal,
                                  erl2context=self.erl2context)

                    # keep a reference to all dynamic setpoint widgets
                    self.__modeWidgets[sys]['dynamic'].append(e)

                    hourNum += 1

                # start off with widgets enabled/disabled appropriately
                self.enableWidgets(sys)

        for row in range(r-1):
            displayContent.rowconfigure(row,weight=0)
        displayContent.rowconfigure(r,weight=1)
        displayContent.columnconfigure(0,weight=1)
        displayContent.columnconfigure(1,weight=1)

        # buttons row
        c = -1

        # left padding
        c += 1
        ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1
        ).grid(row=0, column=c, padx='0', pady=0, sticky='ew')

        # if this is the 'Network' popup, add the Rescan button
        if Erl2Popup.popupType == 'Network':
            c += 1
            self.erl2context['network'].addWidgets(buttonLocs=[{'parent':displayButtons, 'padding':'2 2', 'relief':'solid', 'borderwidth':1,
                                                                'row':0, 'column':c, 'padx':'0 4', 'pady':'0', 'sticky':'ew'}])

        # these three buttons are only for the edit settings popup
        if Erl2Popup.popupType == 'Edit Tank Settings':

            # button: copy from tank
            c += 1
            copyFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
            copyFrame.grid(row=0, column=c, padx='0 4', pady=0, sticky='ew')
            copyButton = tk.Button(copyFrame,
                                   image=self.erl2context['img']['copy-25.png'],
                                   height=40,
                                   width=40,
                                   bd=0,
                                   highlightthickness=0,
                                   activebackground='#DBDBDB',
                                   command=self.ok)
            copyButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(copyFrame, text='Copy from Tank', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', self.ok)

            copyFrame.rowconfigure(0,weight=1)
            copyFrame.columnconfigure(0,weight=0)
            copyFrame.columnconfigure(1,weight=1)

            # button: load from file
            c += 1
            loadFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
            loadFrame.grid(row=0, column=c, padx='0 4', pady=0, sticky='ew')
            loadButton = tk.Button(loadFrame,
                                   image=self.erl2context['img']['load-25.png'],
                                   height=40,
                                   width=40,
                                   bd=0,
                                   highlightthickness=0,
                                   activebackground='#DBDBDB',
                                   command=self.ok)
            loadButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(loadFrame, text='Load from File', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', self.ok)

            loadFrame.rowconfigure(0,weight=1)
            loadFrame.columnconfigure(0,weight=0)
            loadFrame.columnconfigure(1,weight=1)

            # button: save to file
            c += 1
            saveFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
            saveFrame.grid(row=0, column=c, padx='0 4', pady=0, sticky='ew')
            saveButton = tk.Button(saveFrame,
                                   image=self.erl2context['img']['save-25.png'],
                                   height=40,
                                   width=40,
                                   bd=0,
                                   highlightthickness=0,
                                   activebackground='#DBDBDB',
                                   command=self.saveToFile)
            saveButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(saveFrame, text='Save to File', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', self.saveToFile)

            saveFrame.rowconfigure(0,weight=1)
            saveFrame.columnconfigure(0,weight=0)
            saveFrame.columnconfigure(1,weight=1)

        # exit button
        c += 1
        if Erl2Popup.popupType == 'Edit Tank Settings': lbl = 'Cancel'
        else:                                           lbl = 'Close Window'
        exitFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        exitFrame.grid(row=0, column=c, padx='0', pady=0, sticky='ew')
        exitButton = tk.Button(exitFrame,
                               image=self.erl2context['img']['no-25.png'],
                               height=40,
                               width=40,
                               bd=0,
                               highlightthickness=0,
                               activebackground='#DBDBDB',
                               command=self.ok)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(exitFrame, text=lbl, font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.ok)

        exitFrame.rowconfigure(0,weight=1)
        exitFrame.columnconfigure(0,weight=0)
        exitFrame.columnconfigure(1,weight=1)

        # apply button (edit settings only)
        if Erl2Popup.popupType == 'Edit Tank Settings':
            c += 1
            applyFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
            applyFrame.grid(row=0, column=c, padx='4 0', pady=0, sticky='ew')
            applyButton = tk.Button(applyFrame,
                                    image=self.erl2context['img']['yes-25.png'],
                                    height=40,
                                    width=40,
                                    bd=0,
                                    highlightthickness=0,
                                    activebackground='#DBDBDB',
                                    command=self.ok)
            applyButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(applyFrame, text='Apply', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', self.ok)

            applyFrame.rowconfigure(0,weight=1)
            applyFrame.columnconfigure(0,weight=0)
            applyFrame.columnconfigure(1,weight=1)

        # right padding
        c += 1
        ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1
        ).grid(row=0, column=c, padx='0', pady=0, sticky='ew')

        displayButtons.rowconfigure(0,weight=0)
        displayButtons.columnconfigure(0,weight=1)
        for col in range(1,c):
            displayButtons.columnconfigure(col,weight=0)
        displayButtons.columnconfigure(c,weight=1)

        # assuming popup is 312x322, screen is 800x480
        #self.geometry("+244+79")
        self.protocol('WM_DELETE_WINDOW', self.ok)

        # even if this approach fails on macOS, on the PC it seems to work
        self.wait_visibility()
        self.grab_set()
        self.transient(self.erl2context['root'])

        # these are ideas that might work on linux but are problematic on mac + PC
        #self.overrideredirect(1)

    def setToggle(self, sys, ind):

        print (f"setToggle(sys=[{sys}], ind=[{ind}])")

        # change toggle value from 0. to 1. or vice versa
        self.__modeWidgets[sys]['toggle.value'][ind] = 1. - self.__modeWidgets[sys]['toggle.value'][ind]

        # display an image appropriate to the control's state
        onoff = ['off','on'][int(self.__modeWidgets[sys]['toggle.value'][ind])]
        color = ['red','blue'][ind]
        self.__modeWidgets[sys]['toggle'][ind].config(image=self.erl2context['img'][f"radio-{onoff}-{color}-30.png"])

    def enableWidgets(self, sys):

        # what mode is currently selected?
        currMode = self.__modeVar[sys].get()

        # enable/disable toggle controls
        if 'toggle' in self.__modeWidgets[sys]:
            for ind in range(len(self.__modeWidgets[sys]['toggle'])):
                if currMode == MANUAL:
                    self.__modeWidgets[sys]['toggle'][ind].config(state='normal')
                    self.__modeWidgets[sys]['toggle.label'][ind].bind('<Button-1>', lambda event, x=sys, y=ind: self.setToggle(sys=x,ind=y))
                else:
                    self.__modeWidgets[sys]['toggle'][ind].config(state='disabled')
                    self.__modeWidgets[sys]['toggle.label'][ind].unbind('<Button-1>')
                    # if selected, deselect
                    if self.__modeWidgets[sys]['toggle.value'][ind]:
                        self.setToggle(sys,ind)

        # enable/disable manual controls (if applicable)
        if 'manual' in self.__modeWidgets[sys]:
            for w in self.__modeWidgets[sys]['manual']:
                w.setActive(int(currMode == MANUAL))

                # reset manual control to zero if disabling
                if currMode != MANUAL:
                    w.floatValue = 0.
                    w.stringVar.set(w.valToString(0.))

        # enable/disable hysteresis (if applicable)
        if 'hysteresis' in self.__modeWidgets[sys]:
            self.__modeWidgets[sys]['hysteresis'].setActive(int(currMode in [AUTO_DYNAMIC, AUTO_STATIC]))

        # enable/disable auto static parameters
        if 'static' in self.__modeWidgets[sys]:
            self.__modeWidgets[sys]['static'].setActive(int(currMode == AUTO_STATIC))

        # enable/disable auto dynamic parameters
        if 'dynamic' in self.__modeWidgets[sys]:
            for w in self.__modeWidgets[sys]['dynamic']:
                w.setActive(int(currMode == AUTO_DYNAMIC))

    def saveToFile(self, event=None):

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()

        # open a modal window to choose a file to save to
        self.__fileName = fd.asksaveasfilename(parent=self,
                                               title='Save Tank Settings to File...',
                                               initialdir=self.__dirName,
                                               defaultextension='.dat',
                                               )

        # output from asksaveasfilename can be a little weird
        if type(self.__fileName) is tuple:
            if len(self.__fileName) == 0:
                self.__fileName = None
            else:
                self.__fileName = self.__fileName[0]
        elif len(self.__fileName) == 0:
            self.__fileName = None

        # fileName will be None if the user canceled
        if self.__fileName is not None:
            print (f"{__name__}: Debug: saveToFile() returns [{self.__fileName}]")

            # briefly create an Erl2State instance to write out a file of values
            erl2State = Erl2State(fullPath=self.__fileName,
                                  readExisting=False,
                                  erl2context=self.erl2context)
            erl2State.set(valueList = self.getSettings())
            del erl2State

        else:
            print (f"{__name__}: Debug: saveToFile() returns None (canceled)")

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])

    def ok(self, event=None):

        #print (f"{__name__}: Debug: screen width [{self.winfo_screenwidth()}], height [{self.winfo_screenheight()}]")
        #print (f"{__name__}: Debug: popup width [{self.winfo_width()}], height [{self.winfo_height()}]")

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()

        # only ask for confirmation for 'Edit Tank Setting' popup
        if (   Erl2Popup.popupType != 'Edit Tank Settings'
            or mb.askyesno('Debug Confirmation Window',f"Are you sure you want to close the {Erl2Popup.popupType} window?",parent=self)):
            self.destroy()

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])
        #self.onFocusOut()

    def getSettings(self):

        # build a list of tuples for passing to Erl2State
        retVal = []

        # loop through subsystems
        for sys in SUBSYSTEMS:

            # what mode is currently selected?
            retVal.append((sys, 'mode', self.__modeVar[sys].get()))

            # some subsystems may have hysteresis parameter
            if 'hysteresis' in self.__modeWidgets[sys]:
                retVal.append((sys, 'hysteresis', float(self.__modeWidgets[sys]['hysteresis'].stringVar.get())))

            # auto static setpoints
            if 'static' in self.__modeWidgets[sys]:
                retVal.append((sys, 'staticSetpoint', float(self.__modeWidgets[sys]['static'].stringVar.get())))

            # enable/disable auto dynamic parameters
            if 'dynamic' in self.__modeWidgets[sys]:

                # first build the whole list of float values (24 vals expected)
                dynList = []
                for w in self.__modeWidgets[sys]['dynamic']:
                    dynList.append(float(w.stringVar.get()))

                # then assign it into the list of tuples
                retVal.append((sys, 'dynamicSetpoints', dynList))

        # return the list of tuples when done
        return retVal

    # rather than instantiate a new Erl2Popup instance, and risk opening multiple
    # popups at once, provide this classmethod that reads a class attribute and
    # decides whether to instantiate anything (or just co-opt an already-open popup)

    @classmethod
    def openPopup(cls,
                  popupType='About ERL2',
                  erl2context={}):

        if (cls.erl2Popup is not None and cls.erl2Popup.winfo_exists()
                and cls.popupType is not None and cls.popupType == popupType):
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): popup already open")
            cls.erl2Popup.lift()
        else:
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): new popup")
            cls.popupType = popupType
            cls.erl2Popup = Erl2Popup(erl2context=erl2context)

def testPopup(erl2context={}):

    Erl2Popup.openPopup(erl2context=erl2context)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Popup',font='Arial 30 bold').grid(row=0,column=0)
    b = tk.Button(root,
                  text='Click Here',
                  command=lambda: testPopup(erl2context={'root':root}),
                  )
    b.grid(row=2,column=0)

    root.mainloop()

if __name__ == "__main__": main()

