#! /usr/bin/python3

from tkinter import *
from tkinter import ttk
from Erl2Chiller import Erl2Chiller
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Heater import Erl2Heater
from Erl2Image import Erl2Image
from Erl2pH import Erl2pH
from Erl2Temperature import Erl2Temperature

class Erl2Tank:

    def __init__(self, parent, erl2conf=None, img=None):
        self.__parent = parent
        self.__erl2conf = erl2conf
        self.__img = img

        # debugControls attributes
        self.debugControlsEnabled = None
        self.debugControlsVar = IntVar()

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # if necessary, create an object to hold/remember image objects
        if self.__img is None:
            self.__img = Erl2Image(erl2conf=self.__erl2conf)

        # load some images that will be useful later on
        self.__img.addImage('exit25','x-25.png')

        # stylistic stuff
        s = ttk.Style()
        s.configure('TNotebook',tabposition='nw',borderwidth=1,relief='solid')
        s.configure('TNotebook.Tab',font='Arial 16 italic',borderwidth=1,relief='solid',padding='3 3',tabmargins='2 2 2 0',width=8)
        s.configure('TRadiobutton',font='Arial 16')

        # these dicts will hold the objects in this module
        self.__tabs = {}
        self.__frames = {}
        self.__sensors = {}
        self.__controls = {}

        # the top-level element is a notebook (tabbed screens)
        self.__mainTabs = ttk.Notebook(self.__parent,padding='2 2')
        self.__mainTabs.grid(row=0,column=0,pady='0',sticky='nesw')
        self.__mainTabs.rowconfigure(0,weight=1)
        self.__mainTabs.columnconfigure(0,weight=1)

        # trap the tab-change event for special handling
        #self.__mainTabs.bind('<<NotebookTabChanged>>',self.changeTabs)

        # currently we have five tabs
        self.__tabNames = ['Data', 'Temp', 'pH', 'DO', 'Settings']

        # create the tabbed pages (five of them)
        for p in self.__tabNames:

            self.__tabs[p] = ttk.Frame(self.__mainTabs, padding='0',borderwidth=0,relief='solid')
            self.__tabs[p].grid_rowconfigure(0,weight=1)
            self.__tabs[p].grid_columnconfigure(0,weight=1)
            self.__mainTabs.add(self.__tabs[p],text=p,padding=0)

        # add a clock widget in the upper right corner
        clock = Erl2Clock(self.__parent, erl2conf=self.__erl2conf)

        # quickly create 3x4 grids of frames in all tabs (rows first)
        for p in self.__tabNames:
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

        # readout of the current temperature
        self.__sensors['temperature'] = Erl2Temperature(parent=self.__frames['Data'][0][0],
                                                        clones=[self.__frames['Temp'][0][0]],
                                                        row=1,
                                                        column=0,
                                                        places=1,
                                                        erl2conf=self.__erl2conf)

        # temperature labels
        for f in [self.__frames['Data'][0][0], self.__frames['Temp'][0][0]]:
            ttk.Label(f, text=u'Temperature (\u00B0C)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')
            ttk.Label(f, text='25.0', font='Arial 20', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Auto dynamic mode', font='Arial 10 bold italic', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # control widget for the Heater relay
        self.__controls['heater'] = Erl2Heater(parent=self.__frames['Data'][0][1],
                                               clones=[self.__frames['Temp'][0][1]],
                                               disableOn=[True, False],
                                               row=0,
                                               column=0,
                                               erl2conf=self.__erl2conf,
                                               img=self.__img)

        # control widget for the Chiller relay
        self.__controls['chiller'] = Erl2Chiller(parent=self.__frames['Data'][0][1],
                                                 clones=[self.__frames['Temp'][0][1]],
                                                 disableOn=[True, False],
                                                 row=1,
                                                 column=0,
                                                 erl2conf=self.__erl2conf,
                                                 img=self.__img)

        # try loading different image for debugControls! radio button
        self.__img.addImage('radioOff','radio-off-30.png')
        self.__img.addImage('radioOn','radio-on-30.png')

        # debugControls! add radio buttons that will enable/disable heater toggle
        for value , text in [(0, 'Manual'),
                             (1, 'Child'),
                             (2, 'Auto Static'),
                             (3, 'Auto Dynamic')]:
            Radiobutton(self.__frames['Temp'][1][0],
                        indicatoron=0,
                        image=self.__img['radioOff'],
                        selectimage=self.__img['radioOn'],
                        compound='left',
                        font='Arial 16',
                        bd=0,
                        highlightthickness=0,
                        activebackground='#DBDBDB',
                        highlightcolor='#DBDBDB',
                        highlightbackground='#DBDBDB',
                        #bg='#DBDBDB',
                        selectcolor='#DBDBDB',
                        variable=self.debugControlsVar,
                        value=value,
                        text=' '+text,
                        command=self.debugControlsToggle
                        ).grid(row=value,column=0,sticky='w')

        # readout of the current barometric pressure, as reported by the pico-pH
        self.__sensors['pH'] = Erl2pH(parent=self.__frames['Data'][1][0],
                                      clones=[self.__frames['pH'][0][0]],
                                      port='/dev/ttyAMA1',
                                      parameter='pressure',
                                      places=0,
                                      tempSensor=self.__sensors['temperature'],
                                      row=1,
                                      column=0,
                                      erl2conf=self.__erl2conf)

        # pH labels
        for f in [self.__frames['Data'][1][0], self.__frames['pH'][0][0]]:
            ttk.Label(f, text='pH (Total Scale)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')
            ttk.Label(f, text='7.80', font='Arial 20', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Auto static pH mode', font='Arial 10 bold italic', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # add placeholder(s) for dissolved oxygen
        for f in [self.__frames['Data'][2][0], self.__frames['DO'][0][0]]:
            o2sf = ttk.Frame(f, padding='0 0', relief='solid', borderwidth=0)
            o2sf.grid(row=1, column=0, padx='2', pady='0', sticky='nesw')
            o2s = ttk.Label(o2sf, text='705', font='Arial 40 bold', foreground='#A93226')
            o2s.grid(row=0, column=0, sticky='nesw')

            # dissolved oxygen labels
            ttk.Label(f, text=u'DO (\u00B5mol L\u207B\u00B9)', font='Arial 12 bold'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')
            ttk.Label(f, text='700', font='Arial 20', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Off', font='Arial 10 bold italic', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # I'm temporarily adding an exit button for convenience while coding
        exitFrame = ttk.Frame(self.__frames['Settings'][0][0], padding='2 2', relief='solid', borderwidth=0)
        exitFrame.grid(row=0, column=0, padx='2', pady='2', sticky='nwse')
        exitButton = Button(exitFrame, image=self.__img['exit25'], height=40, width=40, bd=0, highlightthickness=0, activebackground='#DBDBDB', command=self.exitprototype)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        exitButton.image = self.__img['exit25']
        ttk.Label(exitFrame, text='Close ERL2 App', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=1, padx='2 2', sticky='e')
        exitFrame.rowconfigure(0,weight=1)
        exitFrame.columnconfigure(0,weight=1)

    ## a method to call whenever we detect a tab change
    #def changeTabs(self, event):
    #    id = self.__mainTabs.select()
    #    p = self.__mainTabs.tab(id, "text")
    #    print (f"{self.__class__.__name__}: Debug: tab changed to [{p}]")

    # temporary: an exit button for convenience while coding
    def exitprototype(self):
        self.__parent.destroy()

    # testing how manipulating one control can en/disable another
    def debugControlsToggle(self):

        for c in ['heater', 'chiller']:
            if c in self.__controls:
                self.__controls[c].setActive(bool(self.debugControlsVar.get()==0))

def main():

    root = Tk()
    #root.configure(bg='grey')
    root.attributes('-fullscreen', True)
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    tank = Erl2Tank(root)
    root.mainloop()

if __name__ == "__main__": main()
