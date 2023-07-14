#! /usr/bin/python3

import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config

class Erl2Image():

    def __init__(self, erl2context={}):
 
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # determine location of main images directory
        self.__imgDir = self.erl2context['conf']['system']['imgDir']

        # this dictionary will hold all of the images used by the system
        self.__img = {}

    def addImage(self, key, file):
 
        # don't reload the image if it's already there
        if key not in self.__img:
            self.__img[key] = tk.PhotoImage(file=self.__imgDir + '/' + file)

    # override [] syntax to return PhotoImage objects
    def __getitem__(self, key):
 
        if key in self.__img:
            return self.__img[key]
        else:
            return None

def main():

    root = tk.Tk()
    img = Erl2Image()
    img.addImage('sample-image','x-25.png')
    ttk.Label(root, image=img['sample-image'],padding='50 50').grid(row=0,column=0)

    root.mainloop()

if __name__ == "__main__": main()

