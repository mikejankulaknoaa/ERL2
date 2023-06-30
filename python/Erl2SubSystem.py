#! /usr/bin/python3

from time import strftime
from tkinter import *
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image

class Erl2SubSystem():

    def __init__(self,
                 type='temperature',
                 radioLocs=[],
                 staticLocs=[],
                 offsetLocs=[],
                 dynamicLocs=[],
                 setpointLocs=[],
                 modeLocs=[],
                 radioImages=['radio-off-30.png','radio-on-30.png'],
                 sensors=[],
                 controls=[],
                 erl2conf=None,
                 img=None):

        self.__radioLocs = radioLocs
        self.__staticLocs = staticLocs
        self.__offsetLocs = offsetLocs
        self.__dynamicLocs = dynamicLocs
        self.__setpointLocs = setpointLocs
        self.__modeLocs = modeLocs
        self.radioImages = radioImages
        self.__sensors = sensors
        self.__controls = controls
        self.__erl2conf = erl2conf
        self.img = img

        # missing! add later
        self.__places = 1

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # if necessary, create an object to hold/remember image objects
        if self.img is None:
            self.img = Erl2Image(erl2conf=self.__erl2conf)

        # load the associated images; just use the image name as the key
        for i in self.radioImages:
            self.img.addImage(i,i)

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
        self.__modeVar = IntVar()
        self.__setpoint = self.__erl2conf['temperature']['setpointDefault']

        # and here is the list of all possible modes
        self.__modeDict = {0:'Manual',
                           1:'Child',
                           2:'Auto Static',
                           3:'Auto Dynamic'}

        # during initialization, the default mode is 2 (auto static)
        self.__modeVar.set(2)

        # add radio buttons to control this subsystem's operating mode
        for loc in self.__radioLocs:
            for value , text in self.__modeDict.items():
                r = Radiobutton(loc['parent'],
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
                            command=self.changeMode
                            )
                r.grid(row=value,column=0,sticky='w')

                # disable "Child" mode for now
                if text == 'Child':
                    r.config(state='disabled')

                self.__radioWidgets.append(r)
            
        # add static setpoint entry fields
        for loc in self.__staticLocs:

            # create the entry fields for the auto static setpoint
            e = ttk.Entry(loc['parent'], width=4, font='Arial 20')
            e.insert(END, self.__erl2conf['temperature']['setpointDefault'])
            e.grid(row=loc['row'],column=loc['column']) #, sticky='s')
            #e.bind('<FocusIn>', self.numpadEntry)

            self.__staticWidgets.append(e)
    
        # add offset entry fields
        for loc in self.__offsetLocs:
            e = ttk.Entry(loc['parent'], width=3, font='Arial 20')
            e.insert(END, self.__erl2conf['temperature']['offsetDefault'])
            e.grid(row=loc['row'],column=loc['column']) #, sticky='s')
            #e.bind('<FocusIn>', self.numpadEntry)

            self.__offsetWidgets.append(e)
    
        # add dynamic setpoint entry fields
        for loc in self.__dynamicLocs:

            # create the dynamic setpoint grid's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='2 2', relief='solid', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='2', sticky='nwse')

            hourNum = 0
            for hourVal in self.__erl2conf['temperature']['dynamicDefault']:

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
                e.insert(END, hourVal)
                e.grid(row=valRow,column=valCol) #, sticky='s')
                #e.bind('<FocusIn>', self.numpadEntry)

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

        # call changeMode here to initialize button (in)activeness
        self.changeMode()

        # begin monitoring the system
        self.monitorSystem()

    # testing how manipulating one control can en/disable another
    def changeMode(self):

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

        # update the setpoint displays
        for w in self.__setpointWidgets:
            w.config(text=f"{float(round(self.__setpoint,self.__places)):.{self.__places}f}")

        # update the mode displays
        for w in self.__modeWidgets:
            w.config(text=self.__modeDict[var] + ' mode')

    def monitorSystem(self):

        # read the current mode of the system
        var = self.__modeVar.get()

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
                hour = int(strftime('%H'))

                # what is the corresponding setpoint?
                self.__setpoint = float(self.__dynamicWidgets[hour].get())

            # what is the current temperature?
            temp = self.__sensors['temperature'].value['temp.degC']

            # what is the allowable offset?
            offset = float(self.__offsetWidgets[0].get())

            ## for debug purposes
            #action = ''

            # determine the correct course of action
            if temp < self.__setpoint-offset:
                action='HEATER'
                self.__controls['heater'].setState(1)
                self.__controls['chiller'].setState(0)
            elif temp > self.__setpoint+offset:
                action='CHILLER'
                self.__controls['heater'].setState(0)
                self.__controls['chiller'].setState(1)
            else:
                self.__controls['heater'].setState(0)
                self.__controls['chiller'].setState(0)

            #print(f"{self.__class__.__name__}: Debug: mode [{self.__modeDict[var]}], hour [{hour}], setpoint [{self.__setpoint}], offset [{offset}] temp [{temp}] action [{action}]")

        # unrecognized mode
        else:
            raise SystemError(f"{self.__class__.__name__}: Error: monitorSystem() invalid mode [{var}]")

        # for now, redraw setpoints by calling changeMode()
        if var>0:
            self.changeMode()

        # wake up every five seconds and see if anything needs adjustement
        self.__radioWidgets[0].after(5000, self.monitorSystem)

def main():

    root = Tk()
    subsystem = Erl2SubSystem(root)
    root.mainloop()

if __name__ == "__main__": main()
