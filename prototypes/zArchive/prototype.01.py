#! /usr/bin/python

from tkinter import *
from tkinter import ttk

class erl2prototype:

    def __init__(self, root):

        root.title('ERL2 Prototype')

        # one frame to encompass everything
        # note: padding on sides is 10, but 5 vertically because the two
        # (row) frames within each pad vertically by 5 as well
        mainframe = ttk.Frame(root, padding='10 5')
        mainframe.grid(column=1, row=1, sticky='nwes')

        # this sets the mainframe to fill the whole window
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        # divide this main frame into header and body
        headerframe = ttk.Frame(mainframe, relief='solid', borderwidth=1)
        headerframe.grid(column=1, row=1, pady='5', sticky='nwe')
        bodyframe = ttk.Frame(mainframe, relief='solid', borderwidth=1)
        bodyframe.grid(column=1, row=2, pady='5', sticky='nwes')

        # this sets up how the header and body frames share space
        # header: only as much height as it needs
        # body: fill the remaining space
        # both: fill all available width
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(1, weight=0)
        mainframe.rowconfigure(2, weight=1)

        # map out the locations with labels
        ttk.Label(headerframe, text='headerOne').grid(column=1, row=1, padx=5, sticky='ew')
        ttk.Label(headerframe, text='headerTwo').grid(column=2, row=1, padx=5, sticky='ew')
        ttk.Label(headerframe, text='headerThree').grid(column=3, row=1, padx=5, sticky='ew')
        ttk.Label(headerframe, text='headerFour').grid(column=4, row=1, padx=5, sticky='ew')

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

