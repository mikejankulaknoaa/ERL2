#! /usr/bin/python3

from math import floor
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image

## Keypad popup is adapted from  code found online here:
## https://stackoverflow.com/questions/63245400/popup-numpad-numeric-keypad-for-multiple-entry-boxes
## and the look is inspired by an image I found here:
## https://www.jqueryscript.net/other/Visual-Numerical-Keyboard-Easy-Numpad.html

class Erl2NumPad(tk.Toplevel):

    # allow only one Erl2NumPad popup at a time
    numPad = None
    entryWidget = None
    varName = None

    # list of buttons (in order of appearance, 4x4 grid)
    BUTTONS = ['7', '8', '9', 'Del', '4', '5', '6', 'Clear', '1', '2', '3', 'Cancel', '0', 'Dot', 'Minus', 'Done']

    def __init__(self, erl2context={}):

        super().__init__()

        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load the associated images
        for i in self.BUTTONS:
            name = f"key{i}.png"
            self.erl2context['img'].addImage(i,name)

        # validate input by typing, if external keyboard is available
        vcmd = self.register(self.validateNumPad)

        # create a Frame to hold everything
        self.__f = ttk.Frame(self, padding='2 2', relief='solid', borderwidth=5)
        self.__f.grid(row=0, column=0, padx='2', pady='2', sticky='nwse')

        # assuming popup is 312x322, screen is 800x480
        self.geometry("+244+79")
        self.protocol('WM_DELETE_WINDOW', self.ok)
        self.overrideredirect(1)

        # use a variable for the display widget
        self.displayVar = tk.StringVar()

        # display field at the top
        self.display = ttk.Entry(self.__f,
                                 textvariable=self.displayVar,
                                 width=12,
                                 font='Arial 24',
                                 justify='right',
                                 validate='key',
                                 validatecommand=(vcmd,'%d','%i','%s','%S'))
        self.display.grid(row=0,column=0,columnspan=4,padx=10,pady=10)

        # when first opening, copy the initial value from the field being edited
        self.displayVar.set('')
        if Erl2NumPad.entryWidget is not None and Erl2NumPad.varName is not None:
            #print (f"{__name__}: Debug: entryWidget is !NOT! None [{Erl2NumPad.entryWidget.getvar(Erl2NumPad.varName)}]")
            self.displayVar.set(Erl2NumPad.entryWidget.getvar(Erl2NumPad.varName))
        #else:
        #    print (f"{__name__}: Debug: entryWidget is None")

        # buttons come next
        for n in range(len(self.BUTTONS)):

            label = self.BUTTONS[n]

            cur = ttk.Button(self.__f, #text=label,
                image=self.erl2context['img'][label],
                command=lambda x=label: self.click(x))
            
            cur.grid(row=floor(n/4)+1, column=(n%4))

        # this is meant to disallow clicks on any other window but the popup
        self.wait_visibility()
        self.grab_set()

    def click(self, label):

        #print (f"{__name__}: Debug: screen width [{self.winfo_screenwidth()}], height [{self.winfo_screenheight()}]")
        #print (f"{__name__}: Debug: popup width [{self.winfo_width()}], height [{self.winfo_height()}]")

        if label == 'Del':
            self.displayVar.set(self.displayVar.get()[:-1])

        elif label == 'Clear':
            self.displayVar.set('')

        elif label == 'Cancel':
            self.ok()

        elif label == 'Done':
            if Erl2NumPad.entryWidget is not None and Erl2NumPad.varName is not None:

                # it's okay if the old value cannot be interpreted as a float, but try
                try:
                    oldVal = float(Erl2NumPad.entryWidget.getvar(Erl2NumPad.varName))
                except:
                    oldVal = None

                # even given the constraints, it's still possible to input invalid values (such as '-.')
                try:
                    newVal = float(self.displayVar.get())
                except:
                    newVal = None

                # insist that newVal is a float, and oldVal is blank or different
                if newVal is not None and (oldVal is None or oldVal != newVal):
                    #print (f"{__name__}: Debug: click('Done'): before [{oldVal}], after [{newVal}]")
                    Erl2NumPad.entryWidget.setvar(Erl2NumPad.varName,self.displayVar.get())

            self.ok()

        elif label == 'Dot':
            # numbers cannot have more than one decimal point
            if '.' not in self.displayVar.get():
                self.displayVar.set(self.displayVar.get()+'.')

        elif label == 'Minus':
            # add/remove minus sign
            if '-' in self.displayVar.get():
                self.displayVar.set(self.displayVar.get()[1:])
            else:
                self.displayVar.set('-'+self.displayVar.get())

        else:
            self.displayVar.set(self.displayVar.get()+label)

    def ok(self):

        self.destroy()
        if Erl2NumPad.entryWidget is not None:
            Erl2NumPad.entryWidget.event_generate("<FocusOut>")

    def validateNumPad(self, d, i, s, S):

        # %d = Type of action (1=insert, 0=delete, -1 for others)
        # %i = index of char string to be inserted/deleted, or -1
        # %P = value of the entry if the edit is allowed
        # %s = value of entry prior to editing
        # %S = the text string being inserted or deleted, if any
        # %v = the type of validation that is currently set
        # %V = the type of validation that triggered the callback
        #      (key, focusin, focusout, forced)
        # %W = the tk name of the widget

        #print (f"{__name__}: Debug: validateNumPad([{d}][{i}],[{s}],[{S}]) called")

        # only validate insertions
        if d != '1':
            return True

        # assume that new input is just one character
        if len(S) > 1:
            #print (f"{__name__}: Debug: validateNumPad([{d}][{i}],[{s}],[{S}]) failed, too long")
            return False

        # require numeric input, . or -
        if S not in '0123456789.-':
            #print (f"{__name__}: Debug: validateNumPad([{d}][{i}],[{s}],[{S}]) failed, bad char")
            return False

        # minus can only be at the beginning
        elif S == '-' and i != '0':
            #print (f"{__name__}: Debug: validateNumPad([{d}][{i}],[{s}],[{S}]) failed, minus in wrong place")
            return False

        # can't have more than one decimal point
        elif S == '.' and '.' in s:
            #print (f"{__name__}: Debug: validateNumPad([{d}][{i}],[{s}],[{S}]) failed, too many decimals")
            return False

        # success
        #print (f"{__name__}: Debug: validateNumPad([{d}][{i}],[{s}],[{S}]) succeeded")
        return True

    # rather than instantiate a new Erl2NumPad instance, and risk opening multiple
    # popups at once, provide this classmethod that reads a class attribute and
    # decides whether to instantiate anything (or just co-opt an already-open popup)

    @classmethod
    def openPopup(cls,
                  entryWidget,
                  erl2context={}):

        cls.entryWidget = entryWidget
        cls.varName = cls.entryWidget['textvariable']

        #print (f"{__name__}: Debug: openPopup([{cls.entryWidget}]): value in [{cls.varName}] is {cls.entryWidget.getvar(cls.varName)}")

        if cls.numPad is not None and cls.numPad.winfo_exists():
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): popup already open")
            cls.numPad.lift()
        else:
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): new popup")
            cls.numPad = Erl2NumPad(erl2context=erl2context)

def testPopup(event):

    Erl2NumPad.openPopup(event.widget)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2NumPad').grid(row=0,column=0)

    v = tk.StringVar()
    e = ttk.Entry(root,textvariable=v)
    e.grid(row=2,column=0)
    e.bind('<Button-1>', testPopup)

    root.mainloop()

if __name__ == "__main__": main()

