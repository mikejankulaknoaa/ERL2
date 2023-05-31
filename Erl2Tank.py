#! /usr/bin/python3

from tkinter import *
from tkinter import ttk
from Erl2Clock import Erl2Clock
from Erl2Temp import Erl2Temp

class Erl2Tank:

    def __init__(self, parent):
        self.__parent = parent

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
        clock = Erl2Clock(self.__parent)

        # add a readout of the current temperature
        temp = Erl2Temp(dataTab)

def main():

    root = Tk()
    tank = Erl2Tank(root)
    root.mainloop()

if __name__ == "__main__": main()
