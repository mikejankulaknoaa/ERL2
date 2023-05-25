#! /usr/bin/python

from tkinter import *
from tkinter import ttk

class erl2prototype:

    def __init__(self, root):

        root.title('ERL2 Prototype')

        # one frame to encompass everything
        # note: padding on sides is 8, but 4 vertically because the two
        # (row) frames within each pad vertically by 4 as well
        mainframe = ttk.Frame(root, padding='8 4')
        mainframe.grid(column=1, row=1, sticky='nwse')

        # this sets the mainframe to fill the whole window
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        # divide this main frame into header and body
        headerframe = ttk.Frame(mainframe, padding='2 4', relief='solid', borderwidth=1)
        headerframe.grid(column=1, row=1, pady='4', sticky='nwse')
        bodyframe = ttk.Frame(mainframe, padding='2 4', relief='solid', borderwidth=1)
        bodyframe.grid(column=1, row=2, pady='4', sticky='nwse')

        # this sets up how the header and body frames share space
        # header: only as much height as it needs
        # body: fill the remaining space
        # both: fill all available width
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(1, weight=0)
        mainframe.rowconfigure(2, weight=1)

        # subframes of the header frame
        h1titleframe = ttk.Frame(headerframe, padding='2 0', relief='solid', borderwidth=1)
        h1titleframe.grid(column=1, row=1, padx='2', sticky='nwse')
        h2logframe = ttk.Frame(headerframe, padding='2 0', relief='solid', borderwidth=1)
        h2logframe.grid(column=2, row=1, padx='2', sticky='nwse')
        h3controlframe = ttk.Frame(headerframe, padding='2 0', relief='solid', borderwidth=1)
        h3controlframe.grid(column=3, row=1, padx='2', sticky='nwse')
        h4clockframe = ttk.Frame(headerframe, padding='0 2', relief='solid', borderwidth=1)
        h4clockframe.grid(column=4, row=1, padx='2', sticky='nwse')

        # I'm not sure how to arrange this except to give the clock half as much space
        headerframe.columnconfigure(1, weight=1)
        headerframe.columnconfigure(2, weight=0)
        headerframe.columnconfigure(3, weight=0)
        headerframe.columnconfigure(4, weight=0)
        headerframe.rowconfigure(1, weight=1)

        # h1 (title) subframes
        h1c1tankframe = ttk.Frame(h1titleframe, relief='solid', borderwidth=1)
        h1c1tankframe.grid(column=1, row=1, padx='2', pady='4', sticky='s')
        ttk.Label(h1c1tankframe, text='TANK 1', font='Arial 26 bold', relief='solid', borderwidth=1).grid(column=1, row=1, sticky='s')
        h1c2treatmentframe = ttk.Frame(h1titleframe, relief='solid', borderwidth=1)
        h1c2treatmentframe.grid(column=2, row=1, padx='2', pady='4', sticky='nwse')
        ttk.Label(h1c2treatmentframe, text='Treatment', font='Arial 18 bold italic').grid(column=2, row=1, sticky='se')
        h1titleframe.columnconfigure(1,weight=1)
        h1titleframe.columnconfigure(2,weight=1)
        h1titleframe.rowconfigure(1,weight=1)

        # h2 (log) subframes
        h2c1fileframe = ttk.Frame(h2logframe, relief='solid', borderwidth=1)
        h2c1fileframe.grid(column=1, row=1, padx='2', pady='4', sticky='nwse')
        ttk.Label(h2c1fileframe, text='Log file name', font='Arial 18').grid(column=1, row=1, padx=2, sticky='nwse')
        h2logframe.columnconfigure(1,weight=1)
        h2logframe.rowconfigure(1,weight=1)

        # h3 (control) subframes
        h3c1controlframe = ttk.Frame(h3controlframe, relief='solid', borderwidth=1)
        h3c1controlframe.grid(column=1, row=1, padx='2', pady='4', sticky='nwse')
        ttk.Label(h3c1controlframe, text='Local control', font='Arial 18 bold italic').grid(column=1, row=1, padx=2, sticky='nwse')
        h3controlframe.columnconfigure(1,weight=1)
        h3controlframe.rowconfigure(1,weight=1)

        # h4 (title) subframes
        h4r1tankframe = ttk.Frame(h4clockframe, relief='solid', borderwidth=1)
        h4r1tankframe.grid(column=1, row=1, padx='4', pady='2', sticky='nwse')
        ttk.Label(h4r1tankframe, text='14:20', font='Arial 16 bold').grid(column=1, row=1, sticky='sw')
        h4r2treatmentframe = ttk.Frame(h4clockframe, relief='solid', borderwidth=1)
        h4r2treatmentframe.grid(column=1, row=2, padx='4', pady='2', sticky='nwse')
        ttk.Label(h4r2treatmentframe, text='1.16.23', font='Arial 12').grid(column=2, row=1, sticky='se')
        h4clockframe.columnconfigure(1,weight=1)
        h4clockframe.rowconfigure(1,weight=1)
        h4clockframe.rowconfigure(2,weight=1)

        # map out the locations with labels
        #ttk.Label(h1titleframe, text='headerOne').grid(column=1, row=1, padx=2, sticky='nwse')
        #ttk.Label(h2logframe, text='headerTwo').grid(column=1, row=1, padx=2, sticky='nwse')
        #ttk.Label(h3controlframe, text='headerThree').grid(column=1, row=1, padx=2, sticky='nwse')
        #ttk.Label(h4clockframe, text='headerFour').grid(column=1, row=1, padx=2, sticky='nwse')

        ttk.Label(bodyframe, text='tempOne').grid(column=1, row=1)
        ttk.Label(bodyframe, text='tempTwo').grid(column=2, row=1)
        ttk.Label(bodyframe, text='tempThree').grid(column=3, row=1)
        ttk.Label(bodyframe, text='tempFour').grid(column=4, row=1)
        ttk.Label(bodyframe, text='phOne').grid(column=1, row=2)
        ttk.Label(bodyframe, text='phTwo').grid(column=2, row=2)
        ttk.Label(bodyframe, text='phThree').grid(column=3, row=2)
        ttk.Label(bodyframe, text='phFour').grid(column=4, row=2)

        # add padding following the example I'm using
        #for child in headerframe.winfo_children():
        #    child.grid_configure(padx=5, pady=5)
        #for child in bodyframe.winfo_children():
        #    child.grid_configure(padx=5, pady=5)

root = Tk()
root.attributes('-fullscreen', True)

erl2prototype(root)
root.mainloop()

