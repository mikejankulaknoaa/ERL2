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
    isOpening = False

    def __init__(self, mac=None, erl2context={}):

        super().__init__()

        self.__mac = mac
        self.erl2context = erl2context

        #print (f"{self.__class__.__name__}: Debug: __init__: mac [{self.__mac}]")

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        self.__mfcAirDecimals = self.erl2context['conf']['mfc.air']['displayDecimals']
        self.__mfcCO2Decimals = self.erl2context['conf']['mfc.co2']['displayDecimals']
        self.__mfcN2Decimals = self.erl2context['conf']['mfc.n2']['displayDecimals']

        self.__mfcAirRange = self.erl2context['conf']['mfc.air']['validRange']
        self.__mfcCO2Range = self.erl2context['conf']['mfc.co2']['validRange']
        self.__mfcN2Range = self.erl2context['conf']['mfc.n2']['validRange']

        # in theory heater and chiller should have reset logic too -- to be added later
        #self.__heaterReset = self.erl2context['conf']['heater']['valueWhenReset']
        #self.__chillerReset = self.erl2context['conf']['chiller']['valueWhenReset']

        self.__mfcAirReset = self.erl2context['conf']['mfc.air']['valueWhenReset']
        self.__mfcCO2Reset = self.erl2context['conf']['mfc.co2']['valueWhenReset']
        self.__mfcN2Reset = self.erl2context['conf']['mfc.n2']['valueWhenReset']

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load some images that will be useful later on
        for img in ['no-25.png', 'yes-25.png',
                    'radio-off-30.png', 'radio-on-30.png',
                    'radio-off-red-30.png', 'radio-on-red-30.png',
                    'radio-off-blue-30.png', 'radio-on-blue-30.png',
                    'checkbox-off-25.png', 'checkbox-on-25.png',
                    'copy-25.png', 'load-25.png', 'save-25.png']:
            self.erl2context['img'].addImage(img, img)

        # the 'Edit Tank Settings' popup needs some extra attributes
        self.__modeVar = {}
        self.__modeWidgets = {}
        self.__listbox = None
        self.__macList = []

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

                # add a control to enable / disable the matplotlib plots
                r += 1
                self.erl2context['startup'].createPlotsWidget(widgetLoc={'parent':displayContent,'row':r})

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

                # loop through child tanks and build up a list of ids and macs
                tankList = []
                self.__macList = []
                matching = None
                for mac in self.erl2context['network'].sortedMacs:
                    tankList.append(self.erl2context['network'].childrenDict[mac]['id'])
                    self.__macList.append(mac)

                    # if we find a mac that matches what was passed in, remember its index
                    if self.__mac is not None and self.__mac == mac:
                        matching = len(self.__macList) - 1
                        #print (f"{self.__class__.__name__}: Debug: __init__: setting matching to [{matching}]")

                var = tk.StringVar()
                var.set(tankList)
                self.__listbox = tk.Listbox(tanksFrame, listvariable=var, selectmode=tk.MULTIPLE, font='Arial 12')
                self.__listbox.grid(row=1,column=0,sticky='nesw')

                # preselect matching mac, if found
                if matching is not None:
                    #print (f"{self.__class__.__name__}: Debug: __init__: selecting [{matching}]")
                    self.__listbox.selection_set(matching)
                    self.__listbox.see(matching)
                    self.__listbox.activate(matching)

            # the three subSystems frames are essentially identical
            sysR = -1
            for sys in SUBSYSTEMS:
                sysR += 1
                sysF = ttk.Frame(editFrame, padding='2', relief='solid', borderwidth=1)
                sysF.grid(row=sysR, column=1, padx='2', pady='2', sticky='nesw')

                # keep track of widgets created
                self.__modeWidgets[sys] = {}
                self.__modeWidgets[sys]['header'] = {}

                # how many decimal places to display?
                dispDecimals = self.erl2context['conf'][sys]['displayDecimals']
                validRg = self.erl2context['conf'][sys]['validRange']

                # subSystem header frame
                headerF = ttk.Frame(sysF, padding='0', relief='solid', borderwidth=0)
                headerF.grid(row=0, column=0, padx=0, pady=0, sticky='nw')

                # subsystem checkbox!
                b = tk.Button(headerF,
                              image=self.erl2context['img']['checkbox-on-25.png'],
                              height=30,
                              width=30,
                              bd=0,
                              highlightthickness=0,
                              activebackground='#DBDBDB',
                              #borderwidth=1,
                              command=lambda x=sys: self.toggleSubSystem(sys=x))
                b.grid(row=0, column=0, padx='0 2', sticky='w')

                # this is the (text) Label shown beside the (image) button widget
                lbl = sys
                if sys == 'temperature':
                    lbl = 'Temperature'
                l = ttk.Label(headerF, text=lbl + ':', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=1, padx='2 0', sticky='w')
                l.bind('<Button-1>', lambda event, x=sys: self.toggleSubSystem(sys=x))

                # keep track of control + label widgets for this checkbox
                self.__modeWidgets[sys]['checkbox'] = b
                self.__modeWidgets[sys]['checkbox.label'] = l
                self.__modeWidgets[sys]['checkbox.value'] = 0.

                # mode frame
                modF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                modF.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')
                l = ttk.Label(modF, text='Mode', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, sticky='nw')
                self.__modeWidgets[sys]['header']['mode'] = l

                # the radiobuttons themselves
                self.__modeVar[sys] = tk.IntVar()
                if 'modeDefault' in self.erl2context['conf'][sys]:
                    self.__modeVar[sys].set(int(self.erl2context['conf'][sys]['modeDefault']))
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
                l = ttk.Label(manF, text='Manual Controls', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, columnspan=2, sticky='nw')
                self.__modeWidgets[sys]['header']['manual'] = l

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
                                  command=lambda x='temperature', y=0: self.toggleHeaterChiller(sys=x,ind=y))
                    b.grid(row=1, column=0, padx='2 2', sticky='w')

                    # this is the (text) Label shown beside the (image) button widget
                    l = ttk.Label(manF, text='Heater', font='Arial 16'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=1, column=1, padx='2 2', sticky='w')
                    l.bind('<Button-1>', lambda event, x='temperature', y=0: self.toggleHeaterChiller(sys=x,ind=y))

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
                                  command=lambda x='temperature', y=1: self.toggleHeaterChiller(sys=x,ind=y))
                    b.grid(row=2, column=0, padx='2 2', sticky='w')

                    # this is the (text) Label shown beside the (image) button widget
                    l = ttk.Label(manF, text='Chiller', font='Arial 16'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=2, column=1, padx='2 2', sticky='w')
                    l.bind('<Button-1>', lambda event, x='temperature', y=1: self.toggleHeaterChiller(sys=x,ind=y))

                    # keep track of control + label widgets for this control
                    self.__modeWidgets[sys]['toggle'].append(b)
                    self.__modeWidgets[sys]['toggle.label'].append(l)

                    # current setting of Chiller defaults to off
                    self.__modeWidgets[sys]['toggle.value'].append(0.)

                elif sys == 'pH':

                    # pH and DO subSystems have MFC (Erl2Entry) controls
                    self.__modeWidgets[sys]['manual'] = []
                    self.__modeWidgets[sys]['manual.reset'] = []
                    self.__modeWidgets[sys]['manual.enabled'] = []

                    # create the entry field for manual control of the Air MFC
                    e = Erl2Entry(entryLoc={'parent':manF,'row':2,'column':1},
                                            labelLoc={'parent':manF,'row':2,'column':0},
                                            label='Air',
                                            width=5,
                                            displayDecimals=self.__mfcAirDecimals,
                                            validRange=self.__mfcAirRange,
                                            initValue=0.,
                                            erl2context=self.erl2context)

                    # keep a reference to this Air MFC control widget
                    self.__modeWidgets[sys]['manual'].append(e)
                    self.__modeWidgets[sys]['manual.reset'].append(self.__mfcAirReset)
                    self.__modeWidgets[sys]['manual.enabled'].append(False)

                    # create the entry field for manual control of the CO2 MFC
                    e = Erl2Entry(entryLoc={'parent':manF,'row':3,'column':1},
                                            labelLoc={'parent':manF,'row':3,'column':0},
                                            label=u'CO\u2082',
                                            width=5,
                                            displayDecimals=self.__mfcCO2Decimals,
                                            validRange=self.__mfcCO2Range,
                                            initValue=0.,
                                            erl2context=self.erl2context)

                    # keep a reference to this CO2 MFC control widget
                    self.__modeWidgets[sys]['manual'].append(e)
                    self.__modeWidgets[sys]['manual.reset'].append(self.__mfcCO2Reset)
                    self.__modeWidgets[sys]['manual.enabled'].append(False)

                elif sys == 'DO':

                    # pH and DO subSystems have MFC (Erl2Entry) controls
                    self.__modeWidgets[sys]['manual'] = []
                    self.__modeWidgets[sys]['manual.reset'] = []
                    self.__modeWidgets[sys]['manual.enabled'] = []

                    # create the entry field for manual control of the N2 MFC
                    e = Erl2Entry(entryLoc={'parent':manF,'row':2,'column':1},
                                            labelLoc={'parent':manF,'row':2,'column':0},
                                            label=u'N\u2082',
                                            width=5,
                                            displayDecimals=self.__mfcN2Decimals,
                                            validRange=self.__mfcN2Range,
                                            initValue=0.,
                                            erl2context=self.erl2context)

                    # keep a reference to this N2 MFC control widget
                    self.__modeWidgets[sys]['manual'].append(e)
                    self.__modeWidgets[sys]['manual.reset'].append(self.__mfcN2Reset)
                    self.__modeWidgets[sys]['manual.enabled'].append(False)

                # auto controls
                autF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                autF.grid(row=1, column=2, padx='2', pady='2', sticky='nesw')
                l = ttk.Label(autF, text='Auto Controls', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, sticky='nw')
                self.__modeWidgets[sys]['header']['auto'] = l

                # create the entry field for the static setpoint
                e = Erl2Entry(entryLoc={'parent':autF,'row':1,'column':1},
                                        labelLoc={'parent':autF,'row':1,'column':0},
                                        label='Static\nSetpoint',
                                        width=5,
                                        displayDecimals=dispDecimals,
                                        validRange=validRg,
                                        initValue=self.erl2context['conf'][sys]['setpointDefault'],
                                        erl2context=self.erl2context)

                # keep a reference to this static setpoint widget
                self.__modeWidgets[sys]['staticSetpoint'] = e

                # create the entry field for hysteresis (temperature only)
                if sys == 'temperature':
                    e = Erl2Entry(entryLoc={'parent':autF,'row':2,'column':1},
                                            labelLoc={'parent':autF,'row':2,'column':0},
                                            label='Hysteresis',
                                            width=5,
                                            displayDecimals=(dispDecimals+2),
                                            validRange=[0.,None],
                                            initValue=self.erl2context['conf'][sys]['hysteresisDefault'],
                                            erl2context=self.erl2context)

                    # keep a reference to this hysteresis widget
                    self.__modeWidgets[sys]['hysteresis'] = e

                # auto dynamic setpoints
                dynF = ttk.Frame(sysF, padding='2', relief='solid', borderwidth=1)
                dynF.grid(row=1, column=3, padx='2', pady='2', sticky='nesw')
                l = ttk.Label(dynF, text='Auto Dynamic Setpoints (by hour of day)', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=0, column=0, columnspan=24, sticky='nw')
                self.__modeWidgets[sys]['header']['dynamicSetpoints'] = l


                # add dynamic setpoint entry fields
                hourNum = 0
                self.__modeWidgets[sys]['dynamicSetpoints'] = []
                self.__modeWidgets[sys]['dynamicSetpoints.labels'] = []
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
                    l = ttk.Label(dynF, text=str(hourNum), font='Arial 12 bold'
                        #, relief='solid', borderwidth=1
                        )
                    l.grid(row=hourRow, column=hourCol, pady=hourPady, sticky='s')

                    # create the entry field for each dynamic setpoint
                    e = Erl2Entry(entryLoc={'parent':dynF,'row':valRow,'column':valCol},
                                  width=5,
                                  font='Arial 16',
                                  displayDecimals=dispDecimals,
                                  validRange=validRg,
                                  initValue=hourVal,
                                  erl2context=self.erl2context)

                    # keep a reference to all dynamic setpoint widgets
                    self.__modeWidgets[sys]['dynamicSetpoints'].append(e)
                    self.__modeWidgets[sys]['dynamicSetpoints.labels'].append(l)

                    hourNum += 1

                # start off with widgets enabled/disabled appropriately
                self.enableWidgets(sys)

        for row in range(r-1):
            displayContent.rowconfigure(row,weight=0)
        displayContent.rowconfigure(r,weight=1)
        displayContent.columnconfigure(0,weight=1)
        displayContent.columnconfigure(1,weight=1)

        # at this point all the Edit Tank Settings widgets should be created, so prepopulate if necessary
        if self.__mac is not None:
            self.copyFromTank(force=True)

        # buttons row
        c = -1

        # left padding
        c += 1
        ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1
        ).grid(row=0, column=c, padx='0', pady=0, sticky='ew')

        # if this is the 'Network' popup, add the Rescan button
        if Erl2Popup.popupType == 'Network' and 'network' in self.erl2context:
            c += 1
            self.erl2context['network'].addWidgets(buttonLocs=[{'parent':displayButtons, 'padding':'2 2', 'relief':'solid', 'borderwidth':1,
                                                                'row':0, 'column':c, 'padx':'0 4', 'pady':'0', 'sticky':'ew'}])

        # these three buttons are only for the edit settings popup
        if Erl2Popup.popupType == 'Edit Tank Settings':

            # button: copy from tank
            copyFrame = ttk.Frame(tanksFrame, padding='2 2', relief='solid', borderwidth=1)
            copyFrame.grid(row=2, column=0, padx=2, pady=2, sticky='esw')
            copyButton = tk.Button(copyFrame,
                                   image=self.erl2context['img']['copy-25.png'],
                                   height=40,
                                   width=40,
                                   bd=0,
                                   highlightthickness=0,
                                   activebackground='#DBDBDB',
                                   command=self.copyFromTank)
            copyButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(copyFrame, text='Copy from Tank', font='Arial 12'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', lambda event: self.copyFromTank())

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
                                   command=self.loadFromFile)
            loadButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(loadFrame, text='Load from File', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', lambda event: self.loadFromFile())

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
            l.bind('<Button-1>', lambda event: self.saveToFile())

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
                               command=self.closeWindow)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(exitFrame, text=lbl, font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', lambda event: self.closeWindow())

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
                                    command=self.applyToTanks)
            applyButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(applyFrame, text='Apply', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', lambda event: self.applyToTanks())

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
        self.protocol('WM_DELETE_WINDOW', self.closeWindow)

        # even if this approach fails on macOS, on the PC it seems to work
        self.wait_visibility()
        self.grab_set()
        self.transient(self.erl2context['root'])

        # these are ideas that might work on linux but are problematic on mac + PC
        #self.overrideredirect(1)

        # indicate that we've finished opening
        Erl2Popup.isOpening = False

    def toggleHeaterChiller(self, sys, ind, redrawWidgets=True):

        #print (f"toggleHeaterChiller(sys=[{sys}], ind=[{ind}])")

        # change toggle value from 0. to 1. or vice versa
        self.__modeWidgets[sys]['toggle.value'][ind] = 1. - self.__modeWidgets[sys]['toggle.value'][ind]

        # after this we'll want to redraw this subSystem's widgets
        if redrawWidgets:
            self.enableWidgets(sys)

    def toggleSubSystem(self, sys, redrawWidgets=True):

        #print (f"toggleSubSystem(sys=[{sys}]")

        # change checkbox value from 0. to 1. or vice versa
        self.__modeWidgets[sys]['checkbox.value'] = 1. - self.__modeWidgets[sys]['checkbox.value']

        # after this we'll want to redraw this subSystem's widgets
        if redrawWidgets:
            self.enableWidgets(sys)

    def enableWidgets(self, sys):

        # is this subSystem enabled at all??
        sysEnabled = bool(self.__modeWidgets[sys]['checkbox.value'])

        # display an image appropriate to the control's state
        onoff = ['off','on'][int(self.__modeWidgets[sys]['checkbox.value'])]
        self.__modeWidgets[sys]['checkbox'].config(image=self.erl2context['img'][f"checkbox-{onoff}-25.png"])

        # what mode is currently selected?
        currMode = self.__modeVar[sys].get()

        # enable/disable radio buttons
        if 'radio' in self.__modeWidgets[sys]:
            for w in self.__modeWidgets[sys]['radio']:
                if sysEnabled:
                    w.config(state='normal')
                else:
                    w.config(state='disabled')

        # enable/disable toggle controls
        if 'toggle' in self.__modeWidgets[sys]:

            # assuming that toggle, toggle.label and toggle.value go hand-in-hand
            assert('toggle.label' in self.__modeWidgets[sys] and len(self.__modeWidgets[sys]['toggle']) == len(self.__modeWidgets[sys]['toggle.label']))
            assert('toggle.value' in self.__modeWidgets[sys] and len(self.__modeWidgets[sys]['toggle']) == len(self.__modeWidgets[sys]['toggle.value']))

            # loop through all three arrays at once
            for ind in range(len(self.__modeWidgets[sys]['toggle'])):

                # display an image appropriate to the control's state
                onoff = ['off','on'][int(self.__modeWidgets[sys]['toggle.value'][ind])]
                color = ['red','blue'][ind]
                self.__modeWidgets[sys]['toggle'][ind].config(image=self.erl2context['img'][f"radio-{onoff}-{color}-30.png"])

                if currMode == MANUAL and sysEnabled:
                    self.__modeWidgets[sys]['toggle'][ind].config(state='normal')
                    self.__modeWidgets[sys]['toggle.label'][ind].bind('<Button-1>', lambda event, x=sys, y=ind: self.toggleHeaterChiller(sys=x,ind=y))
                    self.__modeWidgets[sys]['toggle.label'][ind].config(foreground='')
                else:
                    self.__modeWidgets[sys]['toggle'][ind].config(state='disabled')
                    self.__modeWidgets[sys]['toggle.label'][ind].unbind('<Button-1>')
                    self.__modeWidgets[sys]['toggle.label'][ind].config(foreground='grey')
                    # if selected, deselect
                    if self.__modeWidgets[sys]['toggle.value'][ind]:
                        self.toggleHeaterChiller(sys,ind)

        # enable/disable manual controls (if applicable)
        if 'manual' in self.__modeWidgets[sys]:

            # assuming that manual, manual.reset and manual.enabled go hand-in-hand
            assert('manual.reset' in self.__modeWidgets[sys] and len(self.__modeWidgets[sys]['manual']) == len(self.__modeWidgets[sys]['manual.reset']))
            assert('manual.enabled' in self.__modeWidgets[sys] and len(self.__modeWidgets[sys]['manual']) == len(self.__modeWidgets[sys]['manual.enabled']))

            # loop through all three arrays at once
            for ind in range(len(self.__modeWidgets[sys]['manual'])):
                w = self.__modeWidgets[sys]['manual'][ind]

                if currMode == MANUAL and sysEnabled:
                    w.setActive(1)

                    # if this widget is just changing to active now, apply reset value
                    if not self.__modeWidgets[sys]['manual.enabled'][ind]:
                        #print (f"{self.__class__.__name__}: Debug: enableWidgets: resetting Erl2Entry value to [{self.__modeWidgets[sys]['manual.reset'][ind]}]")
                        w.setValue(self.__modeWidgets[sys]['manual.reset'][ind])
                        self.__modeWidgets[sys]['manual.enabled'][ind] = True

                else:
                    w.setActive(0)

                    # when inactive it looks better to render as zero
                    #print (f"{self.__class__.__name__}: Debug: enableWidgets: disabling Erl2Entry value to [0.]")
                    w.setValue(0.)
                    self.__modeWidgets[sys]['manual.enabled'][ind] = False

        # enable/disable hysteresis (if applicable)
        if 'hysteresis' in self.__modeWidgets[sys]:
            self.__modeWidgets[sys]['hysteresis'].setActive(int(currMode in [AUTO_DYNAMIC, AUTO_STATIC] and sysEnabled))

        # enable/disable auto static parameters
        if 'staticSetpoint' in self.__modeWidgets[sys]:
            self.__modeWidgets[sys]['staticSetpoint'].setActive(int(currMode == AUTO_STATIC and sysEnabled))

        # enable/disable auto dynamic parameters
        if 'dynamicSetpoints' in self.__modeWidgets[sys]:
            for w in self.__modeWidgets[sys]['dynamicSetpoints']:
                w.setActive(int(currMode == AUTO_DYNAMIC and sysEnabled))

        # enable/disable auto dynamic labels
        if 'dynamicSetpoints.labels' in self.__modeWidgets[sys]:
            # label color
            clr = '' # default text color
            if not (currMode == AUTO_DYNAMIC and sysEnabled):
                clr = 'grey'
            for l in self.__modeWidgets[sys]['dynamicSetpoints.labels']:
                l.config(foreground=clr)

        # enable/disable headers (based only on whether subSystem is active)
        if 'header' in self.__modeWidgets[sys]:
            clr = ''
            if not sysEnabled:
                clr = 'grey'
            for hdr in self.__modeWidgets[sys]['header'].keys():
                self.__modeWidgets[sys]['header'][hdr].config(foreground=clr)

    def saveToFile(self):

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()

        # how many subSystems?
        sysCount = 0
        for sys in SUBSYSTEMS:
            if 'checkbox.value' in self.__modeWidgets[sys]:
                sysCount += self.__modeWidgets[sys]['checkbox.value']

        # popup message if no subSystems are selected to save
        if sysCount == 0:
            mb.showinfo('No SubSystems Selected', 'Please use SubSystems checkboxes to indicate which settings you wish to save to a file.', parent=self)

        else:

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
                #print (f"{__name__}: Debug: saveToFile() returns [{self.__fileName}]")

                # briefly create an Erl2State instance to write out a file of values
                erl2State = Erl2State(fullPath=self.__fileName,
                                      readExisting=False,
                                      erl2context=self.erl2context)
                erl2State.set(valueList = self.getSettings())
                del erl2State

            #else:
            #    print (f"{__name__}: Debug: saveToFile() returns None (canceled)")

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])

    def loadFromFile(self):

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()

        # open a modal window to choose a file to load from
        self.__fileName = fd.askopenfilename(parent=self,
                                             title='Load Tank Settings from File...',
                                             initialdir=self.__dirName,
                                             defaultextension='.dat',
                                             )

        # output from askopenfilename can be a little weird
        if type(self.__fileName) is tuple:
            if len(self.__fileName) == 0:
                self.__fileName = None
            else:
                self.__fileName = self.__fileName[0]
        elif len(self.__fileName) == 0:
            self.__fileName = None

        # fileName will be None if the user canceled
        if self.__fileName is not None:
            #print (f"{__name__}: Debug: saveToFile() returns [{self.__fileName}]")

            # lots of things could go wrong here
            retVal = None
            try:
                # briefly create an Erl2State instance to read in a file of values
                erl2State = Erl2State(fullPath=self.__fileName,
                                      readExisting=True,
                                      erl2context=self.erl2context)
                retVal = self.setSettings(erl2State)
                del erl2State

            except:
                retVal = 'cannot read the selected file.'

            # report any errors
            if retVal is not None:
                mb.showerror('File Error', 'Error while Reading Settings from File: ' + retVal, parent=self)

        #else:
        #    print (f"{__name__}: Debug: saveToFile() returns None (canceled)")

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])

    def copyFromTank(self, force=False):

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()

        # read the listbox to see what if anything is selected
        selection = self.__listbox.curselection()

        #print (f"{__name__}: Debug: copyFromTank() result is type [{type(selection).__name__}], length [{len(selection)}]")
        for ind in selection:
            mac = self.__macList[ind]
            #print (f"{__name__}: Debug: copyFromTank() [{ind}][{mac}][{self.__listbox.get(ind)}][{self.erl2context['network'].childrenStates[mac]}]")

        # popup message if nothing is selected to copy from
        if len(selection) == 0:
            mb.showinfo('No Tank Selected', 'Please select which tank you wish to copy settings from.', parent=self)

        else:
            # just use the first-selected tank if there are multiple tanks selected
            ind = selection[0]
            mac = self.__macList[ind]

            # ask for confirmation before copying values (unless force=True)
            if force or mb.askyesno('Confirm Copy from Tank', f"Are you sure you wish to overwrite this window's values "
                                                              f"with settings from {self.__listbox.get(ind)}?", parent=self):

                # set this window's values from the chosen tank's (current) state
                if mac in self.erl2context['network'].childrenStates:
                    #print (f"{__name__}: Debug: copyFromTank(): copying from child/tank state")
                    retVal = self.setSettings(self.erl2context['network'].childrenStates[mac], redrawWidgets=False)

                    # report any errors (unlikely, when copying from in-memory settings)
                    if retVal is not None:
                        mb.showerror('Tank Error', 'Error while Copying Tank Settings from child: ' + retVal, parent=self)

                # now overwrite these (current) tank settings with any prior program defined on the parent side
                if mac in self.erl2context['network'].parentStates:
                    #print (f"{__name__}: Debug: copyFromTank(): copying from parent/controller state")
                    retVal = self.setSettings(self.erl2context['network'].parentStates[mac], redrawWidgets=False)

                    # report any errors (unlikely, when copying from in-memory settings)
                    if retVal is not None:
                        mb.showerror('Tank Error', 'Error while Copying Tank Settings from parent: ' + retVal, parent=self)

                    # set subSystem checkboxes according to whether there's ever been a parent-side program or not
                    for sys in SUBSYSTEMS:
                        self.__modeWidgets[sys]['checkbox.value'] = int(self.erl2context['network'].parentStates[mac].isType(sys))

                # now that all changes have been applied, redraw everything
                for sys in SUBSYSTEMS:
                    self.enableWidgets(sys)

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])

    def applyToTanks(self):

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()

        # read the listbox to see what if anything is selected
        selection = self.__listbox.curselection()

        #print (f"{__name__}: Debug: applyToTanks() result is type [{type(selection).__name__}], length [{len(selection)}]")
        ids = []
        macs = []
        for ind in selection:
            mac = self.__macList[ind]
            print (f"{__name__}: Debug: applyToTanks() [{ind}][{mac}][{self.__listbox.get(ind)}][{self.erl2context['network'].childrenStates[mac]}]")
            ids.append(self.__listbox.get(ind))
            macs.append(mac)

        # popup message if nothing is selected to copy from
        if len(selection) == 0:
            mb.showinfo('No Tank Selected', 'Please select which tank(s) to which you wish to apply these settings.', parent=self)

        else:
            # ask for confirmation before applying new programming to tanks
            if mb.askyesno('Confirm Apply to Tanks',
                           'Are you sure you wish to overwrite the programming in the following ' +
                           'tank(s) with settings from this window?\n\n    ' + '\n    '.join(ids),
                           parent=self):

                # get list of setting tuples suitable for creating Erl2State instances
                thisSet = self.getSettings()

                # loop through selected tanks
                for mac in macs:

                    # tell the Networking module that we want to send these settings to a child tank
                    self.erl2context['network'].sendSettings(mac, thisSet)

                # once all requests processed, close the Edit Tank Settings window
                self.destroy()

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])

    def closeWindow(self):

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
            or mb.askyesno('Confirm Cancelation',f"Are you sure you want to cancel this {Erl2Popup.popupType} operation?",parent=self)):
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

            # make sure the subSystem is enabled
            if 'checkbox.value' in self.__modeWidgets[sys] and  self.__modeWidgets[sys]['checkbox.value'] > 0:

                # what mode is currently selected?
                currMode = self.__modeVar[sys].get()
                retVal.append((sys, 'mode', currMode))

                # send manual settings only if current mode is Manual
                if currMode == MANUAL:

                    # note: this part of the parent/child communication assumes that the
                    # toggle and Erl2Entry controls are presented in the same order in
                    # both parent and child apps

                    # does this subSystem have toggle controls?
                    if 'toggle.value' in self.__modeWidgets[sys]:

                        # toggle.value is already an array of control setting values
                        #print (f"{__name__}: Debug: getSettings({sys}): found toggle settings {self.__modeWidgets[sys]['toggle.value']}")
                        retVal.append((sys, 'toggle', self.__modeWidgets[sys]['toggle.value']))

                    # does this subSystem have Erl2Entry controls?
                    if 'manual' in self.__modeWidgets[sys]:

                        # build an array of float values from the Erl2Entry instances
                        manualVals = []
                        for e in self.__modeWidgets[sys]['manual']:
                            manualVals.append(e.floatValue)
                        #print (f"{__name__}: Debug: getSettings({sys}): found manual settings {manualVals}")
                        retVal.append((sys, 'manual', manualVals))

                # some subsystems may have hysteresis parameter
                if 'hysteresis' in self.__modeWidgets[sys]:
                    retVal.append((sys, 'hysteresis', self.__modeWidgets[sys]['hysteresis'].floatValue))

                # auto static setpoints
                if 'staticSetpoint' in self.__modeWidgets[sys]:
                    retVal.append((sys, 'staticSetpoint', self.__modeWidgets[sys]['staticSetpoint'].floatValue))

                # enable/disable auto dynamic parameters
                if 'dynamicSetpoints' in self.__modeWidgets[sys]:

                    # first build the whole list of float values (24 vals expected)
                    dynList = []
                    for w in self.__modeWidgets[sys]['dynamicSetpoints']:
                        dynList.append(w.floatValue)

                    # then assign it into the list of tuples
                    retVal.append((sys, 'dynamicSetpoints', dynList))

        # return the list of tuples when done
        return retVal

    def setSettings(self,fromState, redrawWidgets=True):

        # something is very wrong if this argument is the wrong type
        assert type(fromState) is Erl2State

        # before beginning, take a moment to verify that state file is consistent
        for sys in SUBSYSTEMS:

            # is this subsystem in the source set?
            if fromState.isType(sys):

                # mode
                if not fromState.isName(sys,'mode'):
                    return f"missing {sys}/mode value."
                tp = type(fromState.get(sys,'mode',None))
                if tp is not int:
                    return f"corrupt {sys}/mode value: expected int, got {tp.__name__}."

                # for these next settings, we need to know if we're in manual mode
                val = fromState.get(valueType=sys, valueName='mode', defaultValue=None)
                if val is not None and val == MANUAL:

                    # toggle and manual settings are both optional, but must be number arrays if present
                    for s in ['toggle','manual']:
                        if fromState.isName(sys,s):
                            val = fromState.get(sys,s,None)
                            if type(val) is not list or len(val) == 0 or type(val[0]) not in (int, float):
                                return f"corrupt {sys}/{s} value: expected a nonempty list of numbers, got {val}."

                # staticSetpoint
                if not fromState.isName(sys,'staticSetpoint'):
                    return f"missing {sys}/staticSetpoint value."
                tp = type(fromState.get(sys,'staticSetpoint',None))
                if tp is not float:
                    return f"corrupt {sys}/staticSetpoint value: expected float, got {tp.__name__}."

                # dynamicSetpoints
                if not fromState.isName(sys,'dynamicSetpoints'):
                    return f"missing {sys}/dynamicSetpoints value."
                array = fromState.get(sys,'dynamicSetpoints',None)
                arrayTp = type(array)
                if arrayTp is not list:
                    return f"corrupt {sys}/dynamicSetpoints value: expected list, got {arrayTp.__name__}."
                if len(array) != 24:
                    return f"corrupt {sys}/dynamicSetpoints value: expected 24 elements, got {len(array)}."
                for ind in range(len(array)):
                    elementTp = type(array[ind])
                    if elementTp is not float:
                        return f"corrupt {sys}/dynamicSetpoints[{ind}] value: expected float, got {elementTp.__name__}."

                # hysteresis (if applicable)
                if 'hysteresis' in self.__modeWidgets[sys]:
                    if not fromState.isName(sys,'hysteresis'):
                        return f"missing {sys}/hysteresis value."
                    tp = type(fromState.get(sys,'hysteresis',None))
                    if tp is not float:
                        return f"corrupt {sys}/hysteresis value: expected float, got {tp.__name__}."

        # loop through subsystems
        for sys in SUBSYSTEMS:

            # is this subsystem in the source set?
            if fromState.isType(sys):

                # make sure this subSystem's checkbox is checked
                if 'checkbox.value' in self.__modeWidgets[sys] and self.__modeWidgets[sys]['checkbox.value'] == 0:

                    # don't enable/disable widgets now b/c we're doing it further down
                    self.toggleSubSystem(sys, redrawWidgets=False)

                # logic for reading mode
                currMode = fromState.get(valueType=sys, valueName='mode', defaultValue=None)
                if currMode is not None and sys in self.__modeVar:
                    #print (f"{__name__}: Debug: setSettings({sys}) mode = [{currMode}]")
                    self.__modeVar[sys].set(int(currMode))

                    # really only want to process toggle + manual settings if mode is manual
                    if currMode == MANUAL:

                        # toggle settings
                        if 'toggle.value' in self.__modeWidgets[sys] and fromState.isName(sys, 'toggle'):

                            # get the list of toggle settings
                            toggleSet = fromState.get(sys, 'toggle', defaultValue=None)

                            # assuming that settings and widgets lists go hand-in-hand
                            assert(len(self.__modeWidgets[sys]['toggle.value']) == len(toggleSet))

                            # for safety's sake I'm going to avoid list assignment
                            for ind in range(len(toggleSet)):
                                self.__modeWidgets[sys]['toggle.value'][ind] = toggleSet[ind]

                        # manual settings
                        if 'manual' in self.__modeWidgets[sys] and fromState.isName(sys, 'manual'):

                            # get the list of manual settings
                            manualSet = fromState.get(sys, 'manual', defaultValue=None)

                            # assuming that settings and widgets lists go hand-in-hand
                            assert(len(self.__modeWidgets[sys]['manual']) == len(manualSet))
                            assert('manual.enabled' in self.__modeWidgets[sys] and len(self.__modeWidgets[sys]['manual.enabled']) == len(manualSet))

                            # loop through Erl2Entry widgets and update their values
                            for ind in range(len(manualSet)):
                                #print (f"{self.__class__.__name__}: Debug: setSettings: setting Erl2Entry value to [{manualSet[ind]}]")
                                self.__modeWidgets[sys]['manual'][ind].setValue(manualSet[ind])

                                # consider this control to be 'enabled' so that its value isn't later reset to its default
                                self.__modeWidgets[sys]['manual.enabled'][ind] = True

                # logic for reading hysteresis and staticSetpoint
                for param in ['hysteresis', 'staticSetpoint']:

                    # does this subsystem have this type of widget?
                    if param in self.__modeWidgets[sys]:
                        w = self.__modeWidgets[sys][param]

                        # is this parameter in the source set?
                        val = fromState.get(valueType=sys, valueName=param, defaultValue=None)
                        if val is not None:
                            #print (f"{__name__}: Debug: setSettings({sys}) {param} = [{val}]")
                            w.setValue(val)

                # logic for reading dynamicSetpoints
                if 'dynamicSetpoints' in self.__modeWidgets[sys]:

                    # list of the hourly widgets to populate
                    wList = self.__modeWidgets[sys]['dynamicSetpoints']

                    # list of the hourly values to assign
                    valList = fromState.get(valueType=sys, valueName='dynamicSetpoints', defaultValue=None)

                    #print (f"{__name__}: Debug: setSettings({sys}) dynamicSetpoints widgets[{len(wList)}], values [{len(valList)}]")

                    # loop through as many as we can
                    for ind in range(min(len(wList), len(valList))):
                        #print (f"{__name__}: Debug: setSettings({sys}) dynamicSetpoints[{ind}]= [{valList[ind]}]")
                        wList[ind].setValue(valList[ind])

                # enable/disable widgets if needed for mode changes
                if redrawWidgets:
                    self.enableWidgets(sys)

        # no errors to report
        return None

    # rather than instantiate a new Erl2Popup instance, and risk opening multiple
    # popups at once, provide this classmethod that reads a class attribute and
    # decides whether to instantiate anything (or just co-opt an already-open popup)

    @classmethod
    def openPopup(cls,
                  popupType='About ERL2',
                  mac=None,
                  erl2context={}):

        if (cls.erl2Popup is not None and cls.erl2Popup.winfo_exists()
                and cls.popupType is not None and cls.popupType == popupType):
            #print (f"{__name__}: Debug: openPopup({popupType}): popup already open")
            cls.erl2Popup.lift()
        elif cls.isOpening:
            #print (f"{__name__}: Debug: openPopup({popupType}): popup in the process of opening")
            pass
        else:
            #print (f"{__name__}: Debug: openPopup({popupType}): new popup")
            cls.popupType = popupType
            cls.isOpening = True
            cls.erl2Popup = Erl2Popup(mac=mac, erl2context=erl2context)

def testPopup(popupType='About ERL2', erl2context={}):

    Erl2Popup.openPopup(popupType=popupType, erl2context=erl2context)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Popup',font='Arial 30 bold').grid(row=0,column=0)
    b = tk.Button(root,
                  text='Edit Tank Settings',
                  command=lambda tp='Edit Tank Settings': testPopup(popupType=tp, erl2context={'root':root}),
                  )
    b.grid(row=1,column=0)
    b = tk.Button(root,
                  text='Network',
                  command=lambda tp='Network': testPopup(popupType=tp, erl2context={'root':root}),
                  )
    b.grid(row=2,column=0)
    b = tk.Button(root,
                  text='Settings',
                  command=lambda tp='Settings': testPopup(popupType=tp, erl2context={'root':root}),
                  )
    b.grid(row=3,column=0)
    b = tk.Button(root,
                  text='About ERL2',
                  command=lambda tp='About ERL2': testPopup(popupType=tp, erl2context={'root':root}),
                  )
    b.grid(row=4,column=0)

    root.mainloop()

if __name__ == "__main__": main()

