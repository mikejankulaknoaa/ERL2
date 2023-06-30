#! /usr/bin/python3

import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config

class Erl2Image():

    def __init__(self,erl2conf=None):
 
        self.erl2conf = erl2conf

        # read in the system configuration file if needed
        if self.erl2conf is None:
            self.erl2conf = Erl2Config()
            #if 'tank' in self.erl2conf.sections() and 'id' in self.erl2conf['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2conf['tank']['id']}]")

        # determine location of main images directory
        self.__imgDir = self.erl2conf['system']['imgDir']

        # this dictionary will hold all of the images used by the system
        self.img = {}

    def addImage(self, key, file):
 
        # don't reload the image if it's already there
        if key not in self.img:
            self.img[key] = tk.PhotoImage(file=self.__imgDir + '/' + file)

    # override [] syntax to return PhotoImage objects
    def __getitem__(self, key):
 
        if key in self.img:
            return self.img[key]
        else:
            return None

def main():

    root = tk.Tk()
    img = Erl2Image()
    root.mainloop()

if __name__ == "__main__": main()

