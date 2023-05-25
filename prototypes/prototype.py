from tkinter import *
from tkinter import ttk
from PIL import ImageTk,Image
from time import strftime
import RPi.GPIO as GPIO

## Keypad popup is adapted from  code found online here:
## https://stackoverflow.com/questions/63245400/popup-numpad-numeric-keypad-for-multiple-entry-boxes
## and the look is inspired by an image I found here:
## https://www.jqueryscript.net/other/Visual-Numerical-Keyboard-Easy-Numpad.html

class NumPad(Toplevel):
    btn_list = ['7', '8', '9', 'Del', '4', '5', '6', 'Clear', '1', '2', '3', 'Cancel', '0', 'Dot', 'Done']
    key_images = []

    def __init__(self, master=None):
        Toplevel.__init__(self, master)
        # assuming popup is 200x200
        self.geometry(f"+{int((root.winfo_width()-200)/2)}+{int((root.winfo_height()-200)/2)}")
        self.protocol('WM_DELETE_WINDOW', self.ok)
        self.overrideredirect(1)
        self.display = ttk.Entry(self, width=12, font='Arial 24', justify='right')
        self.display.grid(row=1,column=1,columnspan=4,padx=10,pady=10)
        self.loadImages()
        self.createWidgets()
        #self.value=value

    def loadImages(self):
        if len(NumPad.key_images) == 0:
             for label in NumPad.btn_list:
                 NumPad.key_images.append(PhotoImage(file='../img/key' + label + '.png'))

    def createWidgets(self):
        # when first opening, copy the initial value from the field being edited
        self.display.delete(0,'end')
        self.display.insert(0,self.master.current_entry.get())

        #btn_list = ['7', '8', '9', 'Del', '4', '5', '6', 'Clear', '1', '2', '3', 'Cancel', '0', 'Dot', 'Done']
        r = 2
        c = 1
        n = 0
        
        for label in NumPad.btn_list:

            # some buttons are sized differently
            if label == '0':
                #w = 15
                sp = 2
            elif label in ['Del', 'Clear', 'Cancel', 'Done']:
                #w = 10
                sp = 1
            else:
                #w = 6
                sp = 1

            cur = ttk.Button(self, #text=label,
                image=NumPad.key_images[n],
                command=lambda x=label: self.click(x))
            
            cur.grid(row=r, column=c, columnspan=sp)
            n += 1
            c += sp
            if c >= 5:
                c = 1
                r += 1

    def click(self, label):
        if label == 'Del':
            self.display.delete(self.display.index('end')-1)
        elif label == 'Clear':
            self.display.delete(0,'end')
        elif label == 'Cancel':
            self.ok()
        elif label == 'Done':
            self.master.current_entry.delete(0,'end')
            self.master.current_entry.insert(0,self.display.get())
            self.ok()
        elif label == 'Dot':
            # numbers cannot have more than one decimal point
            if '.' not in self.display.get():
                self.display.insert('end', '.')
        else:
            self.display.insert('end', label)

    def ok(self):
        self.destroy()
        self.master.focus()
        self.master.numpad = None


class Erl2prototype:

    # on/off logic from https://tkinter.com/on-off-button-switch-python-tkinter-gui-tutorial-161/

    def __init__(self, root):

        # I will eventually move this to a different class
        GPIO.setmode(GPIO.BCM)
        heaterPin = 23
        GPIO.setup(heaterPin, GPIO.OUT)

        # Keep track of the buttons states on/off
        global tempheat_is_on
        global tempchill_is_on
        global phair_is_on
        global phco2_is_on
        tempheat_is_on = False
        tempchill_is_on = False
        phair_is_on = False
        phco2_is_on = False

        # temporary: an exit button for convenience while coding
        def exitprototype():
            root.destroy()

        # Define our switch functions
        def switchtempheat():
            global tempheat_is_on
            # Determine if on or off
            if tempheat_is_on:
                tempheatbutton.config(image=off30)
                tempheatlight.configure(image=lightoff)
                tempheat_is_on = False
                GPIO.output(heaterPin,0)
            else:
                tempheatbutton.config(image=on30)
                tempheatlight.configure(image=lightheat)
                tempheat_is_on = True
                GPIO.output(heaterPin,1)

        def switchtempchill():
            global tempchill_is_on
            # Determine if on or off
            if tempchill_is_on:
                tempchillbutton.config(image=off30)
                tempchilllight.configure(image=lightoff)
                tempchill_is_on = False
            else:
                tempchillbutton.config(image=on30)
                tempchilllight.configure(image=lightchill)
                tempchill_is_on = True

        def switchphair():
            global phair_is_on
            # Determine if on or off
            if phair_is_on:
                phairbutton.config(image=off30)
                airoverride.configure(state='disabled')
                phair_is_on = False
            else:
                phairbutton.config(image=on30)
                airoverride.configure(state='enabled')
                phair_is_on = True

        def switchphco2():
            global phco2_is_on
            # Determine if on or off
            if phco2_is_on:
                phco2button.config(image=off30)
                co2override.configure(state='disabled')
                phco2_is_on = False
            else:
                phco2button.config(image=on30)
                co2override.configure(state='enabled')
                phco2_is_on = True

        # clock/calendar widget adapter from an example found at
        # https://www.geeksforgeeks.org/python-create-a-digital-clock-using-tkinter/#

        def myclock():
            # I am zero-padding the hour, minute and day-of-month, but not the month
            clocktop = strftime('%H:%M')
            clockbot = strftime('%-m.%d.%y')
            myclocktop.config(text=clocktop)
            myclockbot.config(text=clockbot)
            myclockbot.after(1000, myclock)

        #root.title('ERL2 Prototype')

        # load some images for later display (mock-up purposes only)
        loadplot1 = Image.open('../img/plot-1-285.png')
        loadplot2 = Image.open('../img/plot-2-285.png')
        renderplot1 = ImageTk.PhotoImage(loadplot1)
        renderplot2 = ImageTk.PhotoImage(loadplot2)

        # on/off switch images
        on30 = PhotoImage(file="../img/button-green-30.png")
        off30 = PhotoImage(file="../img/button-grey-30.png")
        lightoff = PhotoImage(file="../img/button-grey-30.png")
        lightheat = PhotoImage(file="../img/button-red-30.png")
        lightchill = PhotoImage(file="../img/button-blue-30.png")
        exit25 = PhotoImage(file="../img/x-25.png")

        # one frame to encompass everything
        # note: padding on sides is 8, but 4 vertically because the two
        # (row) frames within each pad vertically by 4 as well
        mainframe = ttk.Frame(root, padding='8 4')
        mainframe.grid(column=1, row=1, sticky='nwse')

        # this sets the mainframe to fill the whole window
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(1, weight=1)

        # tab label images: see bottom of file, these must be stored in global vars

        # change notebook style to put tabs on side
        s = ttk.Style()
        s.configure('TNotebook',tabposition='w',borderwidth=0,padding=0)
        s.configure('TNotebook.Tab',font='Arial 16',padding=4)

        # let's make this into a tabbed-pages prototype
        notebook = ttk.Notebook(mainframe, padding='0')#, relief='solid', borderwidth=1)
        notebook.grid(column=1, row=2, pady='0', sticky='nwse')
        notebook.columnconfigure(1, weight=1)
        notebook.rowconfigure(1, weight=1)

        homepage = ttk.Frame(notebook, padding='0')
        homepage.grid_columnconfigure(1,weight=1)
        homepage.grid_rowconfigure(1,weight=1)
        tab1 = notebook.add(homepage,image=labelhome,padding=0)

        temppage = ttk.Frame(notebook)
        temppage.grid_columnconfigure(1,weight=1)
        temppage.grid_rowconfigure(1,weight=1)
        notebook.add(temppage,image=labeltemp,padding=0)

        phpage = ttk.Frame(notebook)
        phpage.grid_columnconfigure(1,weight=1)
        phpage.grid_rowconfigure(1,weight=1)
        notebook.add(phpage,image=labelph,padding=0)

        o2page = ttk.Frame(notebook)
        o2page.grid_columnconfigure(1,weight=1)
        o2page.grid_rowconfigure(1,weight=1)
        notebook.add(o2page,image=labelo2,padding=0)

        debugpage = ttk.Frame(notebook)
        debugpage.grid_columnconfigure(1,weight=1)
        debugpage.grid_rowconfigure(1,weight=1)
        notebook.add(debugpage,image=labeldebug,padding=0)

        # divide this main frame into header and body
        headerframe = ttk.Frame(mainframe, padding='2 4', relief='solid', borderwidth=1)
        headerframe.grid(column=1, row=1, pady='4', sticky='nwse')
        #bodyframe = ttk.Frame(mainframe, padding='2 2', relief='solid', borderwidth=1)
        #bodyframe.grid(column=1, row=2, pady='4', sticky='nwse')
        bodyframe = ttk.Frame(homepage, padding='2 2', relief='solid', borderwidth=1)
        bodyframe.grid(column=1, row=2, padx='2 0', pady='0', sticky='nwse')

        # this sets up how the header and body frames share space
        # header: only as much height as it needs
        # body: fill the remaining space
        # both: fill all available width
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(1, weight=0)
        mainframe.rowconfigure(2, weight=1)

        # subframes of the header frame
        h1titleframe = ttk.Frame(headerframe, padding='2 0', relief='solid', borderwidth=1)
        h1titleframe.grid(column=2, row=1, padx='2', sticky='nwse')
        h2logframe = ttk.Frame(headerframe, padding='2 0', relief='solid', borderwidth=1)
        h2logframe.grid(column=3, row=1, padx='2', sticky='nwse')
        h3controlframe = ttk.Frame(headerframe, padding='2 0', relief='solid', borderwidth=1)
        h3controlframe.grid(column=4, row=1, padx='2', sticky='nwse')
        h4clockframe = ttk.Frame(headerframe, padding='0 2', relief='solid', borderwidth=1)
        h4clockframe.grid(column=5, row=1, padx='2', sticky='nwse')

        # I've been trying different ways of using up all avaiable space...
        #headerframe.columnconfigure(1, weight=0)
        headerframe.columnconfigure(2, weight=1)
        headerframe.columnconfigure(3, weight=1)
        headerframe.columnconfigure(4, weight=1)
        headerframe.columnconfigure(5, weight=0)
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
        myclocktop = ttk.Label(h4clockframe, text='14:20', font='Arial 16 bold'
            #, relief='solid', borderwidth=1
            )
        myclocktop.grid(column=1, row=1, sticky='n')
        myclockbot = ttk.Label(h4clockframe, text='1.16.23', font='Arial 12'
            #, relief='solid', borderwidth=1
            )
        myclockbot.grid(column=1, row=2, sticky='s')
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
        temp4messageframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        temp4messageframe.grid(column=4, row=1, padx='2', pady='2', sticky='nwse')
        ph1settingframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph1settingframe.grid(column=1, row=2, padx='2', pady='2', sticky='nwse')
        ph2controlframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph2controlframe.grid(column=2, row=2, padx='2', pady='2', sticky='nwse')
        ph3plotframe = ttk.Frame(bodyframe, padding='2 4', relief='solid', borderwidth=1)
        ph3plotframe.grid(column=3, row=2, padx='2', pady='2', sticky='nwse')
        ph4messageframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph4messageframe.grid(column=4, row=2, padx='2', pady='2', sticky='nwse')

        # I've been trying different ways of using up all avaiable space...
        bodyframe.columnconfigure(1, weight=0)
        bodyframe.columnconfigure(2, weight=1)
        bodyframe.columnconfigure(3, weight=0)
        bodyframe.columnconfigure(4, weight=1)
        bodyframe.rowconfigure(1, weight=1)
        bodyframe.rowconfigure(2, weight=1)

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
        tempoverride = ttk.Entry(temp1settingframe, width=4, font='Arial 20')
        tempoverride.insert(END, '25.0')
        tempoverride.grid(column=1, row=3) #, sticky='s')
        tempoverride.bind('<FocusIn>', self.numpadEntry)
        temp1settingframe.columnconfigure(1, weight=1)
        temp1settingframe.rowconfigure(1, weight=1)
        temp1settingframe.rowconfigure(2, weight=0)
        temp1settingframe.rowconfigure(3, weight=1)

        # temperature box 2: controls
        tempheatbutton = Button(temp2controlframe, image=off30, bd=0, command=switchtempheat)
        tempheatbutton.grid(column=1, row=1)
        ttk.Label(temp2controlframe, text='Heater', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='w')
        tempheatlight=ttk.Label(temp2controlframe, image=lightoff)
        tempheatlight.grid(column=3, row=1)

        tempchillbutton = Button(temp2controlframe, image=off30, bd=0, command=switchtempchill)
        tempchillbutton.grid(column=1, row=2)
        ttk.Label(temp2controlframe, text='Chiller', font='Arial 16'
            #, relief='solid', borderwidth=2
            ).grid(column=2, row=2, sticky='w')
        tempchilllight=ttk.Label(temp2controlframe, image=lightoff)
        tempchilllight.grid(column=3, row=2)
        temp2controlframe.columnconfigure(1, weight=0)
        temp2controlframe.columnconfigure(2, weight=1)
        temp2controlframe.columnconfigure(3, weight=1)
        temp2controlframe.rowconfigure(1, weight=1)
        temp2controlframe.rowconfigure(2, weight=1)

        # temperature box 3: plots
        tempplot1=ttk.Label(temp3plotframe, image=renderplot1)
        tempplot1.grid(column=2, row=1)
        tempplot1.image=renderplot1
        tempplot2=ttk.Label(temp3plotframe, image=renderplot2)
        tempplot2.grid(column=2, row=2)
        tempplot2.image=renderplot2
        tempplot3=ttk.Label(temp3plotframe, image=renderplot2)
        tempplot3.grid(column=2, row=3)
        tempplot3.image=renderplot2

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

        # temperature box 4: messages
        temp4statframe = ttk.Frame(temp4messageframe, padding='0 2', relief='solid', borderwidth=1)
        temp4statframe.grid(column=1, row=1, padx='2', pady='2', sticky='nwse')
        temp4warnframe = ttk.Frame(temp4messageframe, padding='0 2', relief='solid', borderwidth=1)
        temp4warnframe.grid(column=1, row=2, padx='2', pady='2', sticky='nwse')
        temp4messageframe.columnconfigure(1, weight=1)
        temp4messageframe.rowconfigure(1, weight=1)
        temp4messageframe.rowconfigure(2, weight=1)

        temp4stat1frame = ttk.Frame(temp4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        temp4stat1frame.grid(column=1, row=1, pady='0', sticky='nwse')
        ttk.Label(temp4stat1frame, text='Statistics', font='Arial 10 bold italic'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        temp4stat2frame = ttk.Frame(temp4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        temp4stat2frame.grid(column=1, row=2, padx='8 0', sticky='nwse')
        ttk.Label(temp4stat2frame, text='Mean:', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(temp4stat2frame, text='25.0', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        temp4stat3frame = ttk.Frame(temp4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        temp4stat3frame.grid(column=1, row=3, padx='8 0', sticky='nwse')
        ttk.Label(temp4stat3frame, text='Stdev:', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(temp4stat3frame, text='0.10', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        temp4stat4frame = ttk.Frame(temp4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        temp4stat4frame.grid(column=1, row=4, padx='8 0', sticky='nwse')
        ttk.Label(temp4stat4frame, text='Target dev:', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(temp4stat4frame, text='0.10', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        temp4statframe.columnconfigure(1, weight=1)
        temp4statframe.rowconfigure(1, weight=0)
        temp4statframe.rowconfigure(2, weight=0)
        temp4statframe.rowconfigure(3, weight=0)
        temp4statframe.rowconfigure(4, weight=0)

        ttk.Label(temp4warnframe, text='Warning:', font='Arial 10 bold italic'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')

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
        phoverride = ttk.Entry(ph1settingframe, width=4, font='Arial 20')
        phoverride.insert(END, '7.80')
        phoverride.grid(column=1, row=3) #, sticky='s')
        phoverride.bind('<FocusIn>', self.numpadEntry)
        ph1settingframe.columnconfigure(1, weight=1)
        ph1settingframe.rowconfigure(1, weight=1)
        ph1settingframe.rowconfigure(2, weight=0)
        ph1settingframe.rowconfigure(3, weight=1)

        # pH box 2: controls
        ph2controlframe = ttk.Frame(bodyframe, padding='2', relief='solid', borderwidth=1)
        ph2controlframe.grid(column=2, row=2, padx='2', pady='2', sticky='nwse')

        ph2controlsub1frame = ttk.Frame(ph2controlframe, padding='0 2') #, relief='solid', borderwidth=1)
        ph2controlsub1frame.grid(column=1, row=1, padx='2', pady='2', sticky='nwse')
        ttk.Label(ph2controlsub1frame, text='Gas flow', font='Arial 12 bold italic'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='s')
        ttk.Label(ph2controlsub1frame, text='(ml min\u207B\u00B9)', font='Arial 8'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='s', padx='16 0')

        ph2controlsub2frame = ttk.Frame(ph2controlframe, padding='0 2') #, relief='solid', borderwidth=1)
        ph2controlsub2frame.grid(column=1, row=2, padx='2', pady='2', sticky='sw')
        ttk.Label(ph2controlsub2frame, text='Air:', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='s')
        ttk.Label(ph2controlsub2frame, text='2000', font='Arial 16 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='s', padx='4 0')

        ph2controlsub3frame = ttk.Frame(ph2controlframe, padding='0 2') #, relief='solid', borderwidth=1)
        ph2controlsub3frame.grid(column=1, row=3, padx='2', pady='2', sticky='nw')
        phairbutton = Button(ph2controlsub3frame, image=off30, bd=0, command=switchphair)
        phairbutton.grid(column=1, row=1)
        airoverride = ttk.Entry(ph2controlsub3frame, width=4, font='Arial 16')
        airoverride.insert(END, '2000')
        airoverride.config(state='disabled')
        airoverride.grid(column=2, row=1, padx='4 0')

        ph2controlsub4frame = ttk.Frame(ph2controlframe, padding='0 2') #, relief='solid', borderwidth=1)
        ph2controlsub4frame.grid(column=1, row=4, padx='2', pady='2', sticky='sw')
        ttk.Label(ph2controlsub4frame, text=u'CO\u2082:', font='Arial 16'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='s')
        ttk.Label(ph2controlsub4frame, text='0.00', font='Arial 16 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='s', padx='4 0')

        ph2controlsub5frame = ttk.Frame(ph2controlframe, padding='0 2') #, relief='solid', borderwidth=1)
        ph2controlsub5frame.grid(column=1, row=5, padx='2', pady='2', sticky='nw')
        phco2button = Button(ph2controlsub5frame, image=off30, bd=0, command=switchphco2)
        phco2button.grid(column=1, row=1)
        co2override = ttk.Entry(ph2controlsub5frame, width=4, font='Arial 16')
        co2override.insert(END, '1.00')
        co2override.config(state='disabled')
        co2override.grid(column=2, row=1, padx='4 0')

        ph2controlframe.columnconfigure(1, weight=1)
        ph2controlframe.rowconfigure(1, weight=0)
        ph2controlframe.rowconfigure(2, weight=1)
        ph2controlframe.rowconfigure(3, weight=1)
        ph2controlframe.rowconfigure(4, weight=1)
        ph2controlframe.rowconfigure(5, weight=1)

        # pH box 3: plots
        phplot1=ttk.Label(ph3plotframe, image=renderplot1)
        phplot1.grid(column=2, row=1)
        phplot1.image=renderplot1
        phplot2=ttk.Label(ph3plotframe, image=renderplot2)
        phplot2.grid(column=2, row=2)
        phplot2.image=renderplot2
        phplot3=ttk.Label(ph3plotframe, image=renderplot2)
        phplot3.grid(column=2, row=3)
        phplot3.image=renderplot2

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

        # pH box 4: messages
        ph4statframe = ttk.Frame(ph4messageframe, padding='0 2', relief='solid', borderwidth=1)
        ph4statframe.grid(column=1, row=1, padx='2', pady='2', sticky='nwse')
        ph4warnframe = ttk.Frame(ph4messageframe, padding='0 2', relief='solid', borderwidth=1)
        ph4warnframe.grid(column=1, row=2, padx='2', pady='2', sticky='nwse')
        ph4messageframe.columnconfigure(1, weight=1)
        ph4messageframe.rowconfigure(1, weight=1)
        ph4messageframe.rowconfigure(2, weight=1)

        ph4stat1frame = ttk.Frame(ph4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat1frame.grid(column=1, row=1, pady='0', sticky='nwse')
        ttk.Label(ph4stat1frame, text='Statistics', font='Arial 10 bold italic'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ph4stat2frame = ttk.Frame(ph4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat2frame.grid(column=1, row=2, padx='8 0', sticky='nwse')
        ttk.Label(ph4stat2frame, text='Mean pH:', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(ph4stat2frame, text='7.80', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ph4stat3frame = ttk.Frame(ph4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat3frame.grid(column=1, row=3, padx='8 0', sticky='nwse')
        ttk.Label(ph4stat3frame, text='Stdev pH:', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(ph4stat3frame, text='0.01', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ph4stat4frame = ttk.Frame(ph4statframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat4frame.grid(column=1, row=4, padx='8 0', sticky='nwse')
        ttk.Label(ph4stat4frame, text='Target dev:', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')

        ph4stat5subframe = ttk.Frame(ph4stat4frame, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat5subframe.grid(column=1, row=5, pady='0', sticky='nwse')

        ph4stat5sub1frame = ttk.Frame(ph4stat5subframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat5sub1frame.grid(column=1, row=1, padx='16 0', sticky='nwse')
        ttk.Label(ph4stat5sub1frame, text='pH:', font='Arial 10'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(ph4stat5sub1frame, text='0.01', font='Arial 10 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ph4stat5sub2frame = ttk.Frame(ph4stat5subframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat5sub2frame.grid(column=1, row=2, padx='16 0', sticky='nwse')
        ttk.Label(ph4stat5sub2frame, text='Air MFC:', font='Arial 10'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(ph4stat5sub2frame, text='5.0', font='Arial 10 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ph4stat5sub3frame = ttk.Frame(ph4stat5subframe, padding='0 0') #, relief='solid', borderwidth=1)
        ph4stat5sub3frame.grid(column=1, row=3, padx='16 0', sticky='nwse')
        ttk.Label(ph4stat5sub3frame, text=u'CO\u2082 MFC:', font='Arial 10'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')
        ttk.Label(ph4stat5sub3frame, text='0.1', font='Arial 10 bold'
            #, relief='solid', borderwidth=1
            ).grid(column=2, row=1, sticky='nw')
        ph4stat5subframe.columnconfigure(1, weight=1)
        ph4stat5subframe.rowconfigure(1, weight=0)
        ph4stat5subframe.rowconfigure(2, weight=0)
        ph4stat5subframe.rowconfigure(3, weight=0)

        ph4statframe.columnconfigure(1, weight=1)
        ph4statframe.rowconfigure(1, weight=0)
        ph4statframe.rowconfigure(2, weight=0)
        ph4statframe.rowconfigure(3, weight=0)
        ph4statframe.rowconfigure(4, weight=0)
        ph4statframe.rowconfigure(5, weight=0)

        ttk.Label(ph4warnframe, text='Warning:', font='Arial 10 bold italic'
            #, relief='solid', borderwidth=1
            ).grid(column=1, row=1, sticky='nw')

        myclock()

        # placeholder for the Temp tab
        tempmsgframe = ttk.Frame(temppage, padding='2 2', relief='solid', borderwidth=1)
        tempmsgframe.grid(column=1, row=1, padx='2 0', pady='0', sticky='nwse')
        tempmsgframe.columnconfigure(1,weight=1)
        tempmsgframe.rowconfigure(1,weight=1)
        tempmsglabel = ttk.Label(tempmsgframe, text='Temperature-Related\nControls', font='Arial 40 bold', justify='center'
            #, relief='solid', borderwidth=1
            )
        #tempmsglabel.grid(column=1, row=1, sticky='nwse')
        tempmsglabel.pack()

        # placeholder for the pH tab
        phmsgframe = ttk.Frame(phpage, padding='2 2', relief='solid', borderwidth=1)
        phmsgframe.grid(column=1, row=1, padx='2 0', pady='0', sticky='nwse')
        phmsgframe.columnconfigure(1,weight=1)
        phmsgframe.rowconfigure(1,weight=1)
        phmsglabel = ttk.Label(phmsgframe, text='pH-Related\nControls', font='Arial 40 bold', justify='center'
            #, relief='solid', borderwidth=1
            )
        #phmsglabel.grid(column=1, row=1, sticky='nwse')
        phmsglabel.pack()

        # placeholder for the Oxygen tab
        o2msgframe = ttk.Frame(o2page, padding='2 2', relief='solid', borderwidth=1)
        o2msgframe.grid(column=1, row=1, padx='2 0', pady='0', sticky='nwse')
        o2msgframe.columnconfigure(1,weight=1)
        o2msgframe.rowconfigure(1,weight=1)
        o2msglabel = ttk.Label(o2msgframe, text='Oxygen-Related\nControls', font='Arial 40 bold', justify='center'
            #, relief='solid', borderwidth=1
            )
        #o2msglabel.grid(column=1, row=1, sticky='nwse')
        o2msglabel.pack()

        # I'm temporarily adding an exit button for convenience while coding
        exitframe = ttk.Frame(debugpage, padding='2 0', relief='solid', borderwidth=1)
        exitframe.grid(column=1, row=1, padx='2', sticky='nwse')
        exitbutton = Button(exitframe, image=exit25, bd=0, command=exitprototype)
        exitbutton.grid(column=1, row=1, sticky='nwse')
        exitbutton.image = exit25
        exitframe.columnconfigure(1,weight=1)
        exitframe.rowconfigure(1,weight=1)

    def numpadEntry(self, event):
        # change current entry
        root.current_entry = event.widget
        # create numpad if does not exist yet
        if root.numpad is None:
            root.numpad = NumPad(root)
        else:
            root.numpad.lift()

root = Tk()
root.attributes('-fullscreen', True)

# create attributes needed for NumPad
root.numpad = None  # NumPad
root.current_entry = None  # currently selected entry

# argh these won't display properly unless they are kept in global variables
labelhome = PhotoImage(file='../img/label_Home_65.png')
labeltemp = PhotoImage(file='../img/label_Temp_65.png')
labelph = PhotoImage(file='../img/label_pH_65.png')
labelo2 = PhotoImage(file='../img/label_Oxygen_65.png')
labeldebug = PhotoImage(file='../img/label_Debug_65.png')

Erl2prototype(root)
root.mainloop()

