#! /usr/bin/python3

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2NumPad import Erl2NumPad

class Erl2Entry():

    def __init__(self,
                 entryLoc={},
                 labelLoc={},
                 label=None,
                 width=4,
                 displayDecimals=1,
                 validRange=None,
                 initValue=0.,
                 erl2conf=None,
                 img=None):

        # save the Erl2Entry-specific parameters in attributes
        self.__entryLoc = entryLoc
        self.__labelLoc = labelLoc
        self.__label = label
        self.__width = width
        self.__displayDecimals = displayDecimals
        self.__validRange = validRange
        self.__initValue = initValue
        self.erl2conf = erl2conf
        self.img = img

        ## create the Frame that will hold the Entry field and its (optional) Label
        #super().__init__(self.__entryLoc['parent'], padding='0 0', relief='solid', borderwidth=0)
        #self.grid(row=self.__entryLoc['row'], column=self.__entryLoc['column'], padx='2', pady='0', sticky='nesw')

        # attributes related to current/valid value of the Entry
        self.__StringVar = tk.StringVar()
        self.__StringVar.set(self.valToString(self.__initValue))
        self.value = float(self.__StringVar.get())

        # a reference to the ttk.Entry widget
        self.widget = None

        # for validation
        vcmd = self.__entryLoc['parent'].register(self.validate)
        ivcmd = self.__entryLoc['parent'].register(self.revert)

        # create the entry field
        self.widget = ttk.Entry(self.__entryLoc['parent'],
                                textvariable=self.__StringVar,
                                validate='focusout',
                                validatecommand=(vcmd,'%P'),
                                invalidcommand=(ivcmd,),
                                width=self.__width,
                                font='Arial 20',
                                justify='right')
        self.widget.grid(row=self.__entryLoc['row'],column=self.__entryLoc['column'], sticky='e')
        self.widget.bind('<Button-1>', self.numpadPopup)

        # this is the Label shown beside the entry widget
        if 'parent' in self.__labelLoc and label is not None:
            ttk.Label(self.__labelLoc['parent'], text=self.__label, font='Arial 14'
                #, relief='solid', borderwidth=1
                ).grid(row=self.__labelLoc['row'], column=self.__labelLoc['column'], padx='2 2', sticky='w')

    def valToString(self, val):

        return(f"{float(round(val,self.__displayDecimals)):.{self.__displayDecimals}f}")

    def validate(self,newString):

        #print (f"{self.__class__.__name__}: Debug: validate({newString})")

        try:
            # make sure this is a floating-point number within range
            newFloat = float(newString)
            #print (f"{self.__class__.__name__}: Debug: validate() float is [{newFloat}]")

            if self.__validRange is not None and (newFloat < self.__validRange[0] or newFloat > self.__validRange[1]):
                mb.showerror(message=f"Range error: value [{newFloat}] is not in range [{self.__validRange[0]}] - [{self.__validRange[1]}]")
                #print (f"{self.__class__.__name__}: Debug: validate() float [{newFloat}] out of range [{self.__validRange[0]},{self.__validRange[1]}]")
                return False

            # reformat String
            self.__StringVar.set(self.valToString(newFloat))
            #print (f"{self.__class__.__name__}: Debug: validate() new StringVal [{self.__StringVar.get()}]")

            # save new value (rounded, if needed)
            self.value = float(self.__StringVar.get())
            #print (f"{self.__class__.__name__}: Debug: validate() new value [{self.value}]")

        except Exception as e:
            mb.showerror(message=f"Validation error")
            #print (f"{self.__class__.__name__}: Debug: validate() failed [{e}]")
            return False

        # signal successful validation
        #print (f"{self.__class__.__name__}: Debug: validate() succeeded")
        return True

    def revert(self):

        self.__StringVar.set(self.valToString(self.value))

    def numpadPopup(self, event):

        #Erl2NumPad(parent=None, entryField=event.widget, erl2conf=self.erl2conf, img=self.img)
        Erl2NumPad.openPopup(event.widget, erl2conf=self.erl2conf, img=self.img)

def main():

    root = tk.Tk()
    f = ttk.Frame(root)
    f.grid(row=0,column=0,sticky='nesw')

    entry1 = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                       labelLoc={'parent':f,'row':0,'column':0},
                       label=u'Temperature (\u00B0C)',
                       width=4,
                       displayDecimals=1,
                       validRange=[10.,40.],
                       initValue=25.1)
    entry2 = Erl2Entry(entryLoc={'parent':f,'row':1,'column':1},
                       labelLoc={'parent':f,'row':1,'column':0},
                       label='pH (Total Scale)',
                       width=4,
                       displayDecimals=2,
                       validRange=[6.,9.],
                       initValue=7.81)
    entry3 = Erl2Entry(entryLoc={'parent':f,'row':2,'column':1})
    root.mainloop()

if __name__ == "__main__": main()

