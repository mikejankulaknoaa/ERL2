#! /usr/bin/python3

from tkinter import *
from tkinter import ttk

class Erl2Image():

    def __init__(self,erl2conf=None):
        self.__erl2conf = erl2conf

        # read in the system configuration file if needed
        if self.__erl2conf is None:
            self.__erl2conf = Erl2Config()
            if 'tank' in self.__erl2conf.sections() and 'id' in self.__erl2conf['tank']:
                print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.__erl2conf['tank']['id']}]")

        # determine location of main images directory
        self.__imgDir = self.__erl2conf['system']['imgDir']

        # this dictionary will hold all of the images used by the system
        self.__img = {}

    def addImage(self, key, file):
        self.__img[key] = PhotoImage(file=self.__imgDir + '/' + file)

    # override [] syntax to return PhotoImage objects
    def __getitem__(self, key):
        if key in self.__img:
            return self.__img[key]
        else:
            return None

def main():

    img = Erl2Image()

if __name__ == "__main__": main()

