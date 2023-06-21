#! /usr/bin/python3

from tkinter import *
from tkinter import ttk
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2pH import Erl2pH
from Erl2Temperature import Erl2Temperature

class Erl2Tank:

    def __init__(self, parent, erl2conf=None):
        self.__parent = parent
        self.__erl2conf = erl2conf

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # create an object to hold/remember image objects
        self.__img = Erl2Image(erl2conf=self.__erl2conf)

        # load some images that will be useful later on
        self.__img.addImage('exit25','x-25.png')

        # stylistic stuff
        s = ttk.Style()
        s.configure('TNotebook',tabposition='nw',borderwidth=1)
        s.configure('TNotebook.Tab',font='Arial 16 italic',borderwidth=1,padding='3 3',width=8)

        # these dicts will hold the objects in this module
        self.__tabs = {}
        self.__frames = {}
        self.__sensors = {}

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

            self.__tabs[p] = ttk.Frame(self.__mainTabs, padding='0')
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
            ttk.Label(f, text=u'Temperature (\u00B0C)', font='Arial 10'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')
            ttk.Label(f, text='25.0', font='Arial 20'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Auto dynamic mode', font='Arial 10 italic'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

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
            ttk.Label(f, text='pH (Total Scale)', font='Arial 10'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')
            ttk.Label(f, text='7.80', font='Arial 20'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Auto static pH mode', font='Arial 10 italic'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # add placeholder(s) for dissolved oxygen
        for f in [self.__frames['Data'][2][0], self.__frames['DO'][0][0]]:
            o2sf = ttk.Frame(f, padding='2 2', relief='solid', borderwidth=0)
            o2sf.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')
            o2s = ttk.Label(o2sf, text='705', font='Arial 40 bold', foreground='#A93226')
            o2s.grid(row=0, column=0, sticky='nesw')

            # dissolved oxygen labels
            ttk.Label(f, text=u'DO (\u00B5mol L\u207B\u00B9)', font='Arial 10'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='n')
            ttk.Label(f, text='700', font='Arial 20'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='n')
            ttk.Label(f, text='Off', font='Arial 10 italic'
                #, relief='solid', borderwidth=1
                ).grid(row=3, column=0, sticky='n')

            for r in range(4):
                f.rowconfigure(r, weight=1)
            f.columnconfigure(0, weight=0)

        # I'm temporarily adding an exit button for convenience while coding
        #exitFrame = ttk.Frame(self.__tabs['Settings'], padding='2 0', relief='solid', borderwidth=1)
        #exitFrame.grid(row=0, column=0, padx='2', sticky='nesw')
        exitButton = Button(self.__frames['Settings'][0][0], image=self.__img['exit25'], bd=0, command=self.exitprototype)
        exitButton.grid(row=0, column=0, sticky='nwse')
        exitButton.image = self.__img['exit25']
        self.__frames['Settings'][0][0].rowconfigure(0,weight=1)
        self.__frames['Settings'][0][0].columnconfigure(0,weight=1)

    ## a method to call whenever we detect a tab change
    #def changeTabs(self, event):
    #    id = self.__mainTabs.select()
    #    p = self.__mainTabs.tab(id, "text")
    #    print (f"{self.__class__.__name__}: Debug: tab changed to [{p}]")

    # temporary: an exit button for convenience while coding
    def exitprototype(self):
        self.__parent.destroy()

def main():

    root = Tk()
    root.attributes('-fullscreen', True)
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)

    tank = Erl2Tank(root)
    root.mainloop()

if __name__ == "__main__": main()
