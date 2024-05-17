import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image

class Erl2About(tk.Toplevel):

    # allow only one Erl2About popup at a time
    erl2About = None

    def __init__(self, erl2context={}):

        super().__init__()

        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # removes the OS window controls, but breaks logic that keeps window on top
        #self.overrideredirect(1)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load some images that will be useful later on
        self.erl2context['img'].addImage('exit','x-25.png')

        # track whether a modal window is open on top of this one or not
        self.modalOpen = False

        # create a Frame to hold everything
        self.__f = ttk.Frame(self, padding='2 2', relief='flat', borderwidth=0)
        self.__f.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')

        # divide the popup frame into top (info) and bottom (buttons) sections
        displayAbout = ttk.Frame(self.__f, padding='2', relief='solid', borderwidth=1)
        displayAbout.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        displayButtons = ttk.Frame(self.__f, padding='0', relief='flat', borderwidth=0)
        displayButtons.grid(row=2, column=0, padx='2', pady='2', sticky='nesw')

        # label for the main info frame
        ttk.Label(displayAbout, text='About ERL2', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')

        # give weight to info frame
        self.__f.rowconfigure(0,weight=1)
        self.__f.rowconfigure(1,weight=0)
        self.__f.columnconfigure(0,weight=1)

        # information about this ERL2 system
        fontleft = 'Arial 14 bold'
        fontright = 'Arial 14'

        r = 1
        ttk.Label(displayAbout, text='ERL2 Version:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(displayAbout, text=self.erl2context['conf']['system']['version'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(displayAbout, text='Device Id:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(displayAbout, text=self.erl2context['conf']['device']['id'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(displayAbout, text='Log Directory:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(displayAbout, text=self.erl2context['conf']['system']['logDir'], font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(displayAbout, text='Logging Frequency:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')

        # elegant way to summarize logging frequency info
        freq = {}
        for sens in ['system']:
            if self.erl2context['conf'][sens]['loggingFrequency'] not in freq:
                freq[self.erl2context['conf'][sens]['loggingFrequency']] = [sens]
            else:
                freq[self.erl2context['conf'][sens]['loggingFrequency']].append(sens)
        if len(freq) == 1:
            txt = str(self.erl2context['conf']['system']['loggingFrequency']) + ' seconds'
        else:
            txt = ""
            num = 0
            for k, v in sorted(freq.items(), key=lambda item: len(item[1])):
                num += 1
                if num < len(freq):
                    txt += f"{', '.join(v)}: {k} seconds; "
                else:
                    txt += f"other sensors: {k} seconds"

        ttk.Label(displayAbout, text=txt, font=fontright, wraplength=300
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(displayAbout, text='System Startup:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(displayAbout, text=self.erl2context['conf']['system']['startup'].astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(displayAbout, text='System Timezone:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ttk.Label(displayAbout, text=str(self.erl2context['conf']['system']['timezone']), font=fontright
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=1, sticky='nw')

        r += 1
        ttk.Label(displayAbout, text='IP Address:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        ipLocs=[{'parent':displayAbout,'row':r,'column':1}]

        r += 1
        ttk.Label(displayAbout, text='MAC Address:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        macLocs=[{'parent':displayAbout,'row':r,'column':1}]

        r += 1
        ttk.Label(displayAbout, text='Last Network Comms:  ', font=fontleft, justify='right'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, sticky='ne')
        netStatusLocs=[{'parent':displayAbout,'row':r,'column':1}]

        for row in range(r-1):
            displayAbout.rowconfigure(row,weight=0)
        displayAbout.rowconfigure(r,weight=1)
        displayAbout.columnconfigure(0,weight=1)
        displayAbout.columnconfigure(1,weight=1)

        # exit button
        exitFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        exitFrame.grid(row=0, column=1, padx='0', pady=0, sticky='ew')
        exitButton = tk.Button(exitFrame,
                               image=self.erl2context['img']['exit'],
                               height=40,
                               width=40,
                               bd=0,
                               highlightthickness=0,
                               activebackground='#DBDBDB',
                               command=self.ok)
        exitButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(exitFrame, text='Close Window', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.ok)

        # padding
        pad0Frame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        pad0Frame.grid(row=0, column=0, padx='0', pady=0, sticky='ew')
        pad2Frame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        pad2Frame.grid(row=0, column=2, padx='0', pady=0, sticky='ew')

        exitFrame.rowconfigure(0,weight=1)
        exitFrame.columnconfigure(0,weight=0)
        exitFrame.columnconfigure(1,weight=1)

        displayButtons.rowconfigure(0,weight=0)
        displayButtons.columnconfigure(0,weight=1)
        displayButtons.columnconfigure(1,weight=0)
        displayButtons.columnconfigure(2,weight=1)

        # assuming popup is 312x322, screen is 800x480
        self.geometry("+244+79")
        self.protocol('WM_DELETE_WINDOW', self.ok)

        # even if this approach fails on macOS, on the PC it seems to work
        self.wait_visibility()
        self.grab_set()
        self.transient(self.erl2context['root'])

        # these are ideas that might work on linux but are problematic on mac + PC
        #self.overrideredirect(1)
        #self.bind("<FocusOut>", self.onFocusOut)

    def onFocusOut(self, event=None):

        print (f"{__name__}: Debug: onFocusOut() called while self.modalOpen is {self.modalOpen}")

        if not self.modalOpen:
            print (f"{__name__}: Debug: trying to lift() -- {type(self)} and {type(self).__bases__}")
            self.__f.after(100,self.lift)

    def ok(self, event=None):

        #print (f"{__name__}: Debug: screen width [{self.winfo_screenwidth()}], height [{self.winfo_screenheight()}]")
        #print (f"{__name__}: Debug: popup width [{self.winfo_width()}], height [{self.winfo_height()}]")

        # ignore this call if the modal is already open
        if self.modalOpen:
            return

        self.modalOpen = True
        #self.grab_release()
        #self.transient()
        if mb.askyesno('Debug Confirmation Window','Are you sure you want to close the About ERL2 window?',parent=self):
            self.destroy()

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])
        #self.onFocusOut()

    # rather than instantiate a new Erl2About instance, and risk opening multiple
    # popups at once, provide this classmethod that reads a class attribute and
    # decides whether to instantiate anything (or just co-opt an already-open popup)

    @classmethod
    def openPopup(cls,
                  erl2context={}):

        if cls.erl2About is not None and cls.erl2About.winfo_exists():
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): popup already open")
            cls.erl2About.lift()
        else:
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): new popup")
            cls.erl2About = Erl2About(erl2context=erl2context)

def testPopup(erl2context={}):

    Erl2About.openPopup(erl2context=erl2context)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2About',font='Arial 30 bold').grid(row=0,column=0)
    b = tk.Button(root,
                  text='Click Here',
                  command=lambda: testPopup(erl2context={'root':root}),
                  )
    b.grid(row=2,column=0)

    root.mainloop()

if __name__ == "__main__": main()

