from os import path
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config

class Erl2Image():

    def __init__(self,
                 moreImgDirs=[],
                 erl2context={}
                 ):

        self.__moreImgDirs = moreImgDirs
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # determine location of main images directory
        self.__imgDir = self.erl2context['conf']['system']['imgDir']

        # this dictionary will hold all of the images used by the system
        self.__img = {}

    def addImage(self, key, file):

        # search more than one directory, potentially
        imgDir = self.__imgDir
        if not path.isfile(f"{imgDir}/{file}"):
            for d in self.__moreImgDirs:
                if path.isfile(f"{d}/{file}"):
                    imgDir = d
                    break

        # don't reload the image if it's already there
        if key not in self.__img:
            self.__img[key] = tk.PhotoImage(file=f"{imgDir}/{file}")

    # override [] syntax to return PhotoImage objects
    def __getitem__(self, key):

        if key in self.__img:
            return self.__img[key]
        else:
            return None

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Image',font='Arial 30 bold').grid(row=0,column=0)
    img = Erl2Image()
    img.addImage('sample-image','x-25.png')
    ttk.Label(root, image=img['sample-image'],padding='50 50').grid(row=1,column=0)

    root.mainloop()

if __name__ == "__main__": main()

