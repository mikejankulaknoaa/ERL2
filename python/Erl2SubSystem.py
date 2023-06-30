#! /usr/bin/python3

from datetime import datetime as dt
import tkinter as tk
from tkinter import ttk
from Erl2Chiller import Erl2Chiller
from Erl2Config import Erl2Config
from Erl2Heater import Erl2Heater
from Erl2Image import Erl2Image
from Erl2VirtualTemp import Erl2VirtualTemp

class Erl2SubSystem():

    def __init__(self,
                 type='temperature',

                 # these controls are unique and aren't cloned to more than one frame
                 radioLoc={},
                 staticLoc={},
                 offsetLoc={},
                 dynamicLoc={},

                 # these displays may be cloned to multiple tabs/frames
                 setpointLocs=[],
                 modeLocs=[],

                 radioImages=['radio-off-30.png','radio-on-30.png'],
                 sensors={},
                 controls={},
                 erl2conf=None,
                 img=None):

        self.__radioLoc = radioLoc
        self.__staticLoc = staticLoc
        self.__offsetLoc = offsetLoc
        self.__dynamicLoc = dynamicLoc

        self.__setpointLocs = setpointLocs
        self.__modeLocs = modeLocs

        self.radioImages = radioImages
        self.__sensors = sensors
        self.__controls = controls
        self.erl2conf = erl2conf
        self.img = img

        # read in the system configuration file if needed
        if self.erl2conf is None:
            self.erl2conf = Erl2Config()
            #if 'tank' in self.erl2conf.sections() and 'id' in self.erl2conf['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2conf['tank']['id']}]")

        # if necessary, create an object to hold/remember image objects
        if self.img is None:
            self.img = Erl2Image(erl2conf=self.erl2conf)

        # load the associated images; just use the image name as the key
        for i in self.radioImages:
            self.img.addImage(i,i)

        # borrow the display settings from the temperature config
        self.__parameter = self.erl2conf['temperature']['displayParameter']
        self.__places = self.erl2conf['temperature']['displayDecimals']

        # remember what widgets are active for this control
        self.__radioWidgets = []
        self.__staticWidgets = []
        self.__offsetWidgets = []
        self.__dynamicWidgets = []

        self.__setpointWidgets = []
        self.__modeWidgets = []

        # remember if this subsystem's associated controls are enabled or not
        self.__controlsEnabled = None

        # the state of this subsystem is described by its mode and active setpoint
        self.__modeVar = tk.IntVar()
        self.__setpoint = self.erl2conf['temperature']['setpointDefault']

        # and here is the list of all possible modes
        self.__modeDict = {0:'Manual',
                           1:'Child',
                           2:'Auto Static',
                           3:'Auto Dynamic'}

        # during initialization, the default mode is 2 (auto static)
        self.__modeVar.set(2)

        # add radio buttons to control this subsystem's operating mode
        for value , text in self.__modeDict.items():
            r = tk.Radiobutton(self.__radioLoc['parent'],
                               indicatoron=0,
                               image=self.img[self.radioImages[0]],
                               selectimage=self.img[self.radioImages[1]],
                               compound='left',
                               font='Arial 16',
                               bd=0,
                               highlightthickness=0,
                               activebackground='#DBDBDB',
                               highlightcolor='#DBDBDB',
                               highlightbackground='#DBDBDB',
                               #bg='#DBDBDB',
                               selectcolor='#DBDBDB',
                               variable=self.__modeVar,
                               value=value,
                               text=' '+text,
                               command=self.applyMode
                               )
            r.grid(row=value,column=0,ipadx=2,ipady=2,sticky='w')

            self.__radioWidgets.append(r)
            
        # create the entry fields for the auto static setpoint
        e = ttk.Entry(self.__staticLoc['parent'], width=4, font='Arial 20')
        e.insert(tk.END, self.erl2conf['temperature']['setpointDefault'])
        e.grid(row=self.__staticLoc['row'],column=self.__staticLoc['column']) #, sticky='s')
        #e.bind('<FocusIn>', self.numpadEntry)
        e.selection_range(0,0)

        self.__staticWidgets.append(e)
    
        # add offset entry fields
        e = ttk.Entry(self.__offsetLoc['parent'], width=3, font='Arial 20')
        e.insert(tk.END, self.erl2conf['temperature']['offsetDefault'])
        e.grid(row=self.__offsetLoc['row'],column=self.__offsetLoc['column']) #, sticky='s')
        #e.bind('<FocusIn>', self.numpadEntry)
        e.selection_range(0,0)

        self.__offsetWidgets.append(e)
    
        # add dynamic setpoint entry fields

        # create the dynamic setpoint grid's base frame as a child of its parent
        f = ttk.Frame(self.__dynamicLoc['parent'], padding='2 2', relief='solid', borderwidth=0)
        f.grid(row=self.__dynamicLoc['row'], column=self.__dynamicLoc['column'], padx='2', pady='2', sticky='nwse')

        hourNum = 0
        for hourVal in self.erl2conf['temperature']['dynamicDefault']:

            # try them in two rows?
            if hourNum < 12:
                hourRow = 0
                hourCol = hourNum
                valRow = 1
                valCol = hourNum
                hourPady = '0 0'
            else:
                hourRow = 2
                hourCol = hourNum-12
                valRow = 3
                valCol = hourNum-12
                hourPady = '4 0'

            # hour label for dynamic setpoints
            ttk.Label(f, text=str(hourNum), font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=hourRow, column=hourCol, pady=hourPady, sticky='s')

            e = ttk.Entry(f, width=5, font='Arial 16', justify='right')
            e.insert(tk.END, hourVal)
            e.grid(row=valRow,column=valCol) #, sticky='s')
            #e.bind('<FocusIn>', self.numpadEntry)
            e.selection_range(0,0)

            self.__dynamicWidgets.append(e)

            hourNum += 1

        # loop through the list of needed setpoint display widgets for this sensor
        for loc in self.__setpointLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text=self.__setpoint, font='Arial 20')
            l.grid(row=0, column=0, sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)

            # keep a list of setpoint display widgets for this sensor
            self.__setpointWidgets.append(l)

        # loop through the list of needed mode display widgets for this sensor
        for loc in self.__modeLocs:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='n')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text=self.__modeDict[self.__modeVar.get()] + ' mode', font='Arial 10 bold italic')
            l.grid(row=0, column=0, sticky='nesw')

            f.rowconfigure(0,weight=1)
            f.columnconfigure(0,weight=1)

            # keep a list of mode display widgets for this sensor
            self.__modeWidgets.append(l)

        # call applyMode here to initialize button (in)activeness
        self.applyMode()

        # set the focus to the first radio button
        self.__radioWidgets[0].focus()

        # begin monitoring the system
        self.monitorSystem()

    # testing how manipulating one control can en/disable another
    def applyMode(self):

        # read the current mode of the system
        var = self.__modeVar.get()

        # enable/disable this subsystem's associated controls as appropriate
        for c in self.__controls.values():
            c.setActive(bool(var==0))

        # enable/disable the static setpoint entry fields as appropriate
        for w in self.__staticWidgets:
            if var==2:
                w.config(state='normal')
            else:
                w.config(state='disabled')

        # enable/disable the offset entry fields as appropriate
        for w in self.__offsetWidgets:
            if var!=0:
                w.config(state='normal')
            else:
                w.config(state='disabled')

        # enable/disable the dynamic setpoint entry fields as appropriate
        for w in self.__dynamicWidgets:
            if var==3:
                w.config(state='normal')
            else:
                w.config(state='disabled')

        # if in Manual mode, force all hardware controls to off
        if var==0:
            for c in self.__controls.values():
                c.setState(0)

        # disable "Child" mode for now
        self.__radioWidgets[1].config(state='disabled')

        # update display widgets to show to current mode and setpoint
        self.updateDisplays()

        # trigger monitorSystem right away to see immediate effects of mode change
        self.monitorSystem(fromApplyMode=True)

    def updateDisplays(self):

        # read the current mode of the system
        var = self.__modeVar.get()

        # format the setpoint for the display widgets
        upd = f"{float(round(self.__setpoint,self.__places)):.{self.__places}f}"

        # note that in Manual mode, the setpoint is meaningless
        if var==0:
            upd = '--'

        # update the setpoint displays
        for w in self.__setpointWidgets:
            w.config(text=upd)

        # update the mode displays
        for w in self.__modeWidgets:
            w.config(text=self.__modeDict[var] + ' mode')

    def monitorSystem(self, fromApplyMode=False):

        # read the current mode of the system
        var = self.__modeVar.get()

        # try to get the current temperature
        if (    'temperature' in self.__sensors
            and hasattr(self.__sensors['temperature'],'value')
            and self.__parameter in self.__sensors['temperature'].value):
            temp = self.__sensors['temperature'].value[self.__parameter]

        # if temperature is missing
        else:
            # change to Manual mode if not already there
            if var>0:
                # make absolutely certain this isn't an infinite loop
                if not fromApplyMode:
                    self.__modeVar.set(0)
                    self.applyMode()
                    var=0

        # no logic to carry out if in Manual mode
        if var==0:
            pass

        # child mode isn't coded yet
        elif var==1:
            raise SystemError(f"{self.__class__.__name__}: Error: monitorSystem() in [{var}][{self.__modeDict[var]}] mode which is not yet implemented")

        # static and dynamic modes share some logic
        elif var in [2,3]:

            ## for debug purposes
            #hour = -1

            # static setpoint
            if var==2:
                self.__setpoint = float(self.__staticWidgets[0].get())

            # dynamic setpoint
            else:
                # what is the current hour of day?
                hour = int(dt.now().strftime('%H'))

                # what is the corresponding setpoint?
                self.__setpoint = float(self.__dynamicWidgets[hour].get())

            # what is the current temperature?
            if (    'temperature' in self.__sensors
                and hasattr(self.__sensors['temperature'],'value')
                and self.__parameter in self.__sensors['temperature'].value):
                temp = self.__sensors['temperature'].value[self.__parameter]
            else:
                temp = float('nan')

            # what is the allowable offset?
            offset = float(self.__offsetWidgets[0].get())

            ## for debug purposes
            #action = ''

            # determine the correct course of action
            if temp < self.__setpoint-offset:
                action='HEATER'
                if 'heater' in self.__controls:
                    self.__controls['heater'].setState(1)
                if 'chiller' in self.__controls:
                    self.__controls['chiller'].setState(0)
            elif temp > self.__setpoint+offset:
                action='CHILLER'
                if 'heater' in self.__controls:
                    self.__controls['heater'].setState(0)
                if 'chiller' in self.__controls:
                    self.__controls['chiller'].setState(1)
            else:
                if 'heater' in self.__controls:
                    self.__controls['heater'].setState(0)
                if 'chiller' in self.__controls:
                    self.__controls['chiller'].setState(0)

            #print(f"{self.__class__.__name__}: Debug: mode [{self.__modeDict[var]}], hour [{hour}], setpoint [{self.__setpoint}], offset [{offset}] temp [{temp}] action [{action}]")

        # unrecognized mode
        else:
            raise SystemError(f"{self.__class__.__name__}: Error: monitorSystem() invalid mode [{var}]")

        # temperature sensors come and go, so make sure the setpoint-related
        # radio buttons are enabled if-and-only-if temperature is available
        if (        'temperature' in self.__sensors
                and hasattr(self.__sensors['temperature'],'online')
                and self.__sensors['temperature'].online
                and hasattr(self.__sensors['temperature'],'value')
                and self.__parameter in self.__sensors['temperature'].value):
            self.__radioWidgets[2].config(state='normal')
            self.__radioWidgets[3].config(state='normal')
        else:
            self.__radioWidgets[2].config(state='disabled')
            self.__radioWidgets[3].config(state='disabled')

        # update display widgets to show to current mode and setpoint
        self.updateDisplays()

        # wake up every five seconds and see if anything needs adjustment
        self.__radioWidgets[0].after(5000, self.monitorSystem)

def main():

    root = tk.Tk()

    tempFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    tempFrame.grid(row=0, column=0, rowspan=4, padx='2', pady='2', sticky='nesw')

    radioFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    radioFrame.grid(row=0, column=3, rowspan=4, padx='2', pady='2', sticky='nesw')

    dynamicFrame = ttk.Frame(root, padding='2', relief='solid', borderwidth=0)
    dynamicFrame.grid(row=4, column=0, columnspan=5, padx='2', pady='2', sticky='nesw')

    virtualtemp = Erl2VirtualTemp(displayLocs=[{'parent':tempFrame,'row':0,'column':0}],
                                  statusLocs=[{'parent':tempFrame,'row':1,'column':0}])

    heater = Erl2Heater(displayLocs=[{'parent':root,'row':0,'column':1}],
                        buttonLocs=[{'parent':root,'row':2,'column':1}])
    chiller = Erl2Chiller(displayLocs=[{'parent':root,'row':1,'column':1}],
                          buttonLocs=[{'parent':root,'row':3,'column':1}])

    subsystem = Erl2SubSystem(radioLoc={'parent':radioFrame,'row':0,'column':0},
                              staticLoc={'parent':root,'row':0,'column':4},
                              offsetLoc={'parent':root,'row':1,'column':4},
                              dynamicLoc={'parent':dynamicFrame,'row':0,'column':0},
                              setpointLocs=[{'parent':root,'row':2,'column':4}],
                              modeLocs=[{'parent':root,'row':3,'column':4}],
                              sensors={'temperature':virtualtemp},
                              controls={'heater':heater,'chiller':chiller})
    root.mainloop()

if __name__ == "__main__": main()

