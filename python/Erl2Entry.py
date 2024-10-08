import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2NumPad import Erl2NumPad
from Erl2State import Erl2State

class Erl2Entry():

    def __init__(self,
                 parent=None,
                 entryLoc={},
                 labelLoc={},
                 label=None,
                 width=4,
                 font='Arial 20',
                 labelFont='Arial 14',
                 displayDecimals=1,
                 validRange=None,
                 initValue=0.,
                 onChange=None,
                 onChangeArg=None,
                 erl2context={}):

        # save the Erl2Entry-specific parameters in attributes
        self.__parent = parent
        self.__entryLoc = entryLoc
        self.__labelLoc = labelLoc
        self.__label = label
        self.__width = width
        self.__font = font
        self.__labelFont = labelFont
        self.__displayDecimals = displayDecimals
        self.__validRange = validRange
        self.__initValue = initValue
        self.__onChange = onChange
        self.__onChangeArg = onChangeArg
        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # use 'root' as parent window if not explicitly passed
        if self.__parent is None:
            self.__parent = self.erl2context['root']

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # attributes related to current/valid value of the Entry
        self.stringVar = tk.StringVar(value=self.valToString(self.__initValue))
        self.floatValue = float(self.stringVar.get())

        # and whether the entry field is active or not
        self.enabled = 1

        # a reference to the ttk.Entry widget (and its label)
        self.widget = None
        self.labelWidget = None

        # for validation
        vcmd = self.__entryLoc['parent'].register(self.validateEntry)

        # create the entry field
        e = ttk.Entry(self.__entryLoc['parent'],
                      textvariable=self.stringVar,
                      validate='focusout',
                      validatecommand=(vcmd,'%P'),
                      width=self.__width,
                      font=self.__font,
                      justify='right')
        e.grid(row=self.__entryLoc['row'],column=self.__entryLoc['column'], sticky='e')
        e.bind('<Button-1>', self.numPadPopup)
        #e.bind('<Tab>', self.tabHandler)
        e.selection_clear()

        # remember the entry widget
        self.widget = e

        # this is the Label shown beside the entry widget
        if 'parent' in self.__labelLoc and label is not None:
            l = ttk.Label(self.__labelLoc['parent'], text=self.__label, font=self.__labelFont
                #, relief='solid', borderwidth=1
                )
            l.grid(row=self.__labelLoc['row'], column=self.__labelLoc['column'], padx='2 2', sticky='w')

            # remember the entry widget's label
            self.labelWidget = l

    def valToString(self, val):

        return(f"{float(round(val,self.__displayDecimals)):.{self.__displayDecimals}f}")

    def validateEntry(self,newString):

        #print (f"{self.__class__.__name__}: Debug: validateEntry({newString})")

        try:
            # in this case there's no effective change in value
            if self.floatValue == float(newString):

                # make sure number formatting is kept consistent in the display
                self.revertEntry()

            # make sure this is a floating-point number within range
            newFloat = float(newString)
            #print (f"{self.__class__.__name__}: Debug: validateEntry() float is [{newFloat}]")

            # if a range is specified for this value, validate against it
            if self.__validRange is not None:

                msg = None

                # defined range -- both minimum and maximum
                if (    self.__validRange[0] is not None
                    and self.__validRange[1] is not None
                    and (newFloat < self.__validRange[0] or newFloat > self.__validRange[1])):

                    msg = f"Value [{newFloat}] is not in the range [{self.__validRange[0]}] - [{self.__validRange[1]}]"

                # defined minimum only
                elif (    self.__validRange[0] is not None
                      and newFloat < self.__validRange[0]):

                    msg = f"Value [{newFloat}] is not greater than or equal to [{self.__validRange[0]}]"

                # defined maximum only
                elif (    self.__validRange[1] is not None
                      and newFloat > self.__validRange[1]):

                    msg = f"Value [{newFloat}] is not less than or equal to [{self.__validRange[1]}]"

                if msg is not None:
                    self.revertEntry()
                    #print (f"{self.__class__.__name__}: Debug: validateEntry(): {msg}")
                    mb.showerror(title='Range Error', message=msg, parent=self.erl2context['root'])
                    return False

            # reformat String (only if it changes anything)
            if self.stringVar.get() != self.valToString(newFloat):
                self.stringVar.set(self.valToString(newFloat))
                #print (f"{self.__class__.__name__}: Debug: validateEntry() new stringVal [{self.stringVar.get()}]")

            # save new value (rounded, if needed)
            self.floatValue = float(self.stringVar.get())
            #print (f"{self.__class__.__name__}: Debug: validateEntry() new floatValue [{self.floatValue}]")

        except Exception as e:
            self.revertEntry()
            #print (f"{self.__class__.__name__}: Debug: validateEntry() failed [{e}]")
            mb.showerror(message=f"Validation error", parent=self.erl2context['root'])
            return False

        # trigger other actions in the parent if needed
        if self.__onChange is not None:
            if self.__onChangeArg is not None:
                self.__onChange(self.__onChangeArg)
            else:
                self.__onChange()

        # signal successful validation
        #print (f"{self.__class__.__name__}: Debug: validateEntry() succeeded")
        return True

    def revertEntry(self):

        # take no action unless the revert-to value is different from what's there already
        if self.stringVar.get() != self.valToString(self.floatValue):
            self.stringVar.set(self.valToString(self.floatValue))

    def setActive(self, enabled=1):

        if enabled:
            self.widget.config(state='normal')
        else:
            self.widget.config(state='disabled')

        # grey out the entry widget's label if disabled
        if self.labelWidget is not None:
            clr = '' # default text color
            if not enabled:
                clr = 'grey'
            self.labelWidget.config(foreground=clr)

        self.enabled = enabled

    def setValue(self, newVal):

        # right now just require that the new value is a float
        if type(newVal) is float:

            # set the internal float and then update the display with formatted value
            self.floatValue = round(newVal, self.__displayDecimals)
            self.stringVar.set(self.valToString(self.floatValue))

    def numPadPopup(self, event):

        # don't open a popup if the field is disabled
        if self.enabled:

            # check numPad setting, but default to opening the popup if not set
            if self.erl2context['state'].get('system','numPad',1):
                Erl2NumPad.openPopup(event.widget, parent=self.__parent, erl2context=self.erl2context)

    #def tabHandler(self,event):
    #    return 'break'

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Entry',font='Arial 30 bold').grid(row=0,column=0)

    f = ttk.Frame(root)
    f.grid(row=1,column=0,sticky='nesw')

    entry1 = Erl2Entry(entryLoc={'parent':f,'row':0,'column':1},
                       labelLoc={'parent':f,'row':0,'column':0},
                       label=u'Temperature (\u00B0C)',
                       width=4,
                       displayDecimals=1,
                       validRange=[10.,40.],
                       initValue=25.1,
                       erl2context={'root':root})
    entry2 = Erl2Entry(entryLoc={'parent':f,'row':1,'column':1},
                       labelLoc={'parent':f,'row':1,'column':0},
                       label='pH (Total Scale)',
                       width=4,
                       displayDecimals=2,
                       validRange=[6.,9.],
                       initValue=7.81,
                       erl2context={'root':root})
    entry3 = Erl2Entry(entryLoc={'parent':f,'row':2,'column':1},
                       erl2context={'root':root})
    root.mainloop()

if __name__ == "__main__": main()

