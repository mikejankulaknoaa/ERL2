#! /usr/bin/python

from tkinter import *
from tkinter import ttk
from PIL import ImageTk,Image

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
        bodyframe = ttk.Frame(mainframe, padding='2 2', relief='solid', borderwidth=1)
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

        # I've been trying different ways of using up all avaiable space...
        headerframe.columnconfigure(1, weight=1)
        headerframe.columnconfigure(2, weight=1)
        headerframe.columnconfigure(3, weight=1)
        headerframe.columnconfigure(4, weight=0)
        headerframe.rowconfigure(1, weight=1)

        # h1 (title) grid contents
        ttk.Label(h1titleframe, text='TANK 1', font='Arial 26 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, padx='0 2', sticky='nsw')
        ttk.Label(h1titleframe, text='Treatment', font='Arial 18 bold italic'
            #, relief='solid', borderwidth=2
            ).grid(column=2, row=1, padx='2 0', sticky='nsw')
        h1titleframe.columnconfigure(1,weight=1)
        h1titleframe.columnconfigure(2,weight=1)
        h1titleframe.rowconfigure(1,weight=1)

        # h2 (log) grid contents
        ttk.Label(h2logframe, text='Log file name', font='Arial 18'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, padx=2, sticky='ns')
        h2logframe.columnconfigure(1,weight=1)
        h2logframe.rowconfigure(1,weight=1)

        # h3 (control) grid contents
        ttk.Label(h3controlframe, text='Local control', font='Arial 18 bold italic'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, padx=2, sticky='ns')
        h3controlframe.columnconfigure(1,weight=1)
        h3controlframe.rowconfigure(1,weight=1)

        # h4 (title) grid contents
        ttk.Label(h4clockframe, text='14:20', font='Arial 16 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='n')
        ttk.Label(h4clockframe, text='1.16.23', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='s')
        h4clockframe.columnconfigure(1,weight=1)
        h4clockframe.rowconfigure(1,weight=1)
        h4clockframe.rowconfigure(2,weight=1)

        # subframes of the body frame
        temp1settingframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        temp1settingframe.grid(column=1, row=1, padx='2', pady='2', sticky='nwse')
        temp2controlframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        temp2controlframe.grid(column=2, row=1, padx='2', pady='2', sticky='nwse')
        temp3plotframe = ttk.Frame(bodyframe, padding='2 4', relief='solid', borderwidth=1)
        temp3plotframe.grid(column=3, row=1, padx='2', pady='2', sticky='nwse')
        temp4statsframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        temp4statsframe.grid(column=4, row=1, padx='2', pady='2', sticky='nwse')
        ph1settingframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph1settingframe.grid(column=1, row=2, padx='2', pady='2', sticky='nwse')
        ph2controlframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph2controlframe.grid(column=2, row=2, padx='2', pady='2', sticky='nwse')
        ph3plotframe = ttk.Frame(bodyframe, padding='2 4', relief='solid', borderwidth=1)
        ph3plotframe.grid(column=3, row=2, padx='2', pady='2', sticky='nwse')
        ph4statsframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph4statsframe.grid(column=4, row=2, padx='2', pady='2', sticky='nwse')

        # I've been trying different ways of using up all avaiable space...
        bodyframe.columnconfigure(1, weight=0)
        bodyframe.columnconfigure(2, weight=1)
        bodyframe.columnconfigure(3, weight=0)
        bodyframe.columnconfigure(4, weight=1)
        bodyframe.rowconfigure(1, weight=1)
        bodyframe.rowconfigure(2, weight=1)

        # load some images for later display (mock-up purposes only)
        load1 = Image.open('/home/ocedadmin/Desktop/img/plot-1-300.png')
        load2 = Image.open('/home/ocedadmin/Desktop/img/plot-2-300.png')
        render1 = ImageTk.PhotoImage(load1)
        render2 = ImageTk.PhotoImage(load2)

        #
        # temperature row
        #

        # temperature box 1: settings
        ttk.Label(temp1settingframe, text='25.1', font='Arial 40 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='s')
        ttk.Label(temp1settingframe, text=u'Temp (\u00B0C)', font='Arial 10'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='n')
        #tempdefault = StringVar(root)
        tempoverride = ttk.Entry(temp1settingframe, width=4
            #, textvariable=tempdefault
            , font='Arial 20'
            )
        tempoverride.insert(END, '25.0')
        tempoverride.grid(column=1, row=3) #, sticky='s')
        temp1settingframe.columnconfigure(1, weight=1)
        temp1settingframe.rowconfigure(1, weight=1)
        temp1settingframe.rowconfigure(2, weight=0)
        temp1settingframe.rowconfigure(3, weight=1)

        # temperature box 2: controls
        ttk.Label(temp2controlframe, text='tempTwo').grid(column=1, row=1)

        # temperature box 3: plots
        tempplot1=ttk.Label(temp3plotframe, image=render1)
        tempplot1.grid(column=2, row=1)
        tempplot1.image=render1
        tempplot2=ttk.Label(temp3plotframe, image=render2)
        tempplot2.grid(column=2, row=2)
        tempplot2.image=render2
        tempplot3=ttk.Label(temp3plotframe, image=render2)
        tempplot3.grid(column=2, row=3)
        tempplot3.image=render2

        # temperature plots: x axis labels
        tempplotxframe = ttk.Frame(temp3plotframe) #, relief='solid', borderwidth=1)
        tempplotxframe.grid(column=2, row=4, sticky='nwse')
        ttk.Label(tempplotxframe, text='0', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(tempplotxframe, text='6', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ttk.Label(tempplotxframe, text='12', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=3, row=1, sticky='n')
        ttk.Label(tempplotxframe, text='18', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=4, row=1, sticky='ne')
        ttk.Label(tempplotxframe, text='24', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=5, row=1, sticky='ne')
        tempplotxframe.columnconfigure(1, weight=1)
        tempplotxframe.columnconfigure(2, weight=1)
        tempplotxframe.columnconfigure(3, weight=1)
        tempplotxframe.columnconfigure(4, weight=1)
        tempplotxframe.columnconfigure(5, weight=1)
        tempplotxframe.rowconfigure(1, weight=1)

        # temperature plots: y axis labels
        tempplotyframe = ttk.Frame(temp3plotframe) #, relief='solid', borderwidth=1)
        tempplotyframe.grid(column=1, row=1, sticky='nwse')
        ttk.Label(tempplotyframe, text='27', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='ne')
        ttk.Label(tempplotyframe, text='25', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='e')
        ttk.Label(tempplotyframe, text='23', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=3, sticky='se')
        tempplotyframe.columnconfigure(1, weight=1)
        tempplotyframe.rowconfigure(1, weight=1)
        tempplotyframe.rowconfigure(2, weight=1)
        tempplotyframe.rowconfigure(3, weight=1)

        ttk.Label(temp3plotframe, text='Heat', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='e')
        ttk.Label(temp3plotframe, text='Chill', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=3, sticky='e')

        # temperature box 4: stats
        ttk.Label(temp4statsframe, text='tempFour').grid(column=1, row=1)

        #
        # pH row
        #

        # pH box 1: settings
        ttk.Label(ph1settingframe, text='7.81', font='Arial 40 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='s')
        ttk.Label(ph1settingframe, text='pH (total)', font='Arial 10'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='n')
        #phdefault = StringVar(root)
        phoverride = ttk.Entry(ph1settingframe, width=4
            #, textvariable=phdefault
            , font='Arial 20'
            )
        phoverride.insert(END, '7.80')
        phoverride.grid(column=1, row=3) #, sticky='s')
        ph1settingframe.columnconfigure(1, weight=1)
        ph1settingframe.rowconfigure(1, weight=1)
        ph1settingframe.rowconfigure(2, weight=0)
        ph1settingframe.rowconfigure(3, weight=1)

        # pH box 2: controls
        ttk.Label(ph2controlframe, text='phTwo').grid(column=1, row=1)

        # pH box 3: plots
        phplot1=ttk.Label(ph3plotframe, image=render1)
        phplot1.grid(column=2, row=1)
        phplot1.image=render1
        phplot2=ttk.Label(ph3plotframe, image=render2)
        phplot2.grid(column=2, row=2)
        phplot2.image=render2
        phplot3=ttk.Label(ph3plotframe, image=render2)
        phplot3.grid(column=2, row=3)
        phplot3.image=render2

        # pH plots: x axis labels
        phplotxframe = ttk.Frame(ph3plotframe) #, relief='solid', borderwidth=1)
        phplotxframe.grid(column=2, row=4, sticky='nwse')
        ttk.Label(phplotxframe, text='0', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(phplotxframe, text='6', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ttk.Label(phplotxframe, text='12', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=3, row=1, sticky='n')
        ttk.Label(phplotxframe, text='18', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=4, row=1, sticky='ne')
        ttk.Label(phplotxframe, text='24', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=5, row=1, sticky='ne')
        phplotxframe.columnconfigure(1, weight=1)
        phplotxframe.columnconfigure(2, weight=1)
        phplotxframe.columnconfigure(3, weight=1)
        phplotxframe.columnconfigure(4, weight=1)
        phplotxframe.columnconfigure(5, weight=1)
        phplotxframe.rowconfigure(1, weight=1)

        # pH plots: y axis labels
        phplotyframe = ttk.Frame(ph3plotframe) #, relief='solid', borderwidth=1)
        phplotyframe.grid(column=1, row=1, sticky='nwse')
        ttk.Label(phplotyframe, text='8.1', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='ne')
        ttk.Label(phplotyframe, text='7.9', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='e')
        ttk.Label(phplotyframe, text='7.7', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=3, sticky='se')
        phplotyframe.columnconfigure(1, weight=1)
        phplotyframe.rowconfigure(1, weight=1)
        phplotyframe.rowconfigure(2, weight=1)
        phplotyframe.rowconfigure(3, weight=1)

        ttk.Label(ph3plotframe, text='Air', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=2, sticky='e')
        ttk.Label(ph3plotframe, text=u'CO\u2082', font='Arial 14'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=3, sticky='e')

        # pH box 4: stats
        ttk.Label(ph4statsframe, text='phFour').grid(column=1, row=1)

        # add padding following the example I'm using
        #for child in headerframe.winfo_children():
        #    child.grid_configure(padx=5, pady=5)
        #for child in bodyframe.winfo_children():
        #    child.grid_configure(padx=5, pady=5)

root = Tk()
root.attributes('-fullscreen', True)

erl2prototype(root)
root.mainloop()

