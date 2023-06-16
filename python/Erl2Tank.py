#! /usr/bin/python3

from tkinter import *
from tkinter import ttk
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Temperature import Erl2Temperature

class Erl2Tank:

    def __init__(self, parent, config=None):
        self.__parent = parent
        self.config = config

        # read in the system configuration file if needed
        if self.config is None:
            self.config = Erl2Config()
            if 'tank' in self.config.sections() and 'id' in self.config['tank']:
                print (f"Erl2Tank: Tank Id is [{self.config['tank']['id']}]")

        # stylistic stuff
        s = ttk.Style()
        s.configure('TNotebook',tabposition='n',borderwidth=0,padding=0)
        s.configure('TNotebook.Tab',font='Arial 16 italic',padding=4)

        # the top-level element is a notebook (tabbed screens)
        mainTabs = ttk.Notebook(self.__parent, padding='0')
        mainTabs.grid(column=1, row=1, pady='0', sticky='nwse')
        mainTabs.columnconfigure(1, weight=1)
        mainTabs.rowconfigure(1, weight=1)

        dataTab = ttk.Frame(mainTabs, padding='0')
        dataTab.grid_columnconfigure(1,weight=1)
        dataTab.grid_rowconfigure(1,weight=1)
        mainTabs.add(dataTab,text='Data',padding=0)

        tempTab = ttk.Frame(mainTabs)
        tempTab.grid_columnconfigure(1,weight=1)
        tempTab.grid_rowconfigure(1,weight=1)
        mainTabs.add(tempTab,text='Temp',padding=0)

        phTab = ttk.Frame(mainTabs)
        phTab.grid_columnconfigure(1,weight=1)
        phTab.grid_rowconfigure(1,weight=1)
        mainTabs.add(phTab,text='pH',padding=0)

        o2Tab = ttk.Frame(mainTabs)
        o2Tab.grid_columnconfigure(1,weight=1)
        o2Tab.grid_rowconfigure(1,weight=1)
        mainTabs.add(o2Tab,text='DO',padding=0)

        settingsTab = ttk.Frame(mainTabs)
        settingsTab.grid_columnconfigure(1,weight=1)
        settingsTab.grid_rowconfigure(1,weight=1)
        mainTabs.add(settingsTab,text='Settings',padding=0)

        # add a clock widget
        clock = Erl2Clock(self.__parent, config=self.config)

        # add a readout of the current temperature
        temp = Erl2Temperature(dataTab, config=self.config)

def main():

    root = Tk()
    tank = Erl2Tank(root)
    root.mainloop()

if __name__ == "__main__": main()
