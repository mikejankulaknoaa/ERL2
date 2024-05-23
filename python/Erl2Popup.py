import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image

class Erl2Popup(tk.Toplevel):

    # allow only one Erl2Popup popup at a time
    erl2Popup = None
    popupType = None

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

        # read these useful parameters from Erl2Config
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

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

        # divide the popup frame into top (content) and bottom (buttons) sections
        displayContent = ttk.Frame(self.__f, padding='2', relief='solid', borderwidth=1)
        displayContent.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        displayButtons = ttk.Frame(self.__f, padding='0', relief='flat', borderwidth=0)
        displayButtons.grid(row=2, column=0, padx='2', pady='2', sticky='nesw')

        # label for the main content frame
        ttk.Label(displayContent, text=Erl2Popup.popupType, font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')

        # give weight to info frame
        self.__f.rowconfigure(0,weight=1)
        self.__f.rowconfigure(1,weight=0)
        self.__f.columnconfigure(0,weight=1)

        # information about this ERL2 system
        fontleft = 'Arial 14 bold'
        fontright = 'Arial 14'

        # keep track of rows in the content frame
        r = 0

        # the 'About ERL2' popup...
        if Erl2Popup.popupType == 'About ERL2':

            r += 1
            ttk.Label(displayContent, text='ERL2 Version:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['system']['version'], font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='Device Id:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['device']['id'], font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='Log Directory:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['system']['logDir'], font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='Logging Frequency:  ', font=fontleft, justify='right'
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

            ttk.Label(displayContent, text=txt, font=fontright, wraplength=300
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='System Startup:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=self.erl2context['conf']['system']['startup'].astimezone(self.__timezone).strftime(self.__dtFormat), font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            r += 1
            ttk.Label(displayContent, text='System Timezone:  ', font=fontleft, justify='right'
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=0, sticky='ne')
            ttk.Label(displayContent, text=str(self.__timezone), font=fontright
                #, relief='solid', borderwidth=1
                ).grid(row=r, column=1, sticky='nw')

            # these items are only relevant if network is defined
            if 'network' in self.erl2context and self.erl2context['network'] is not None:
                r += 1
                ttk.Label(displayContent, text='Device Type:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                typeLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='Device Name:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                nameLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='Network Interface:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                interfaceLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='IP Address:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                ipLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='MAC Address:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                macLocs=[{'parent':displayContent,'row':r,'column':1}]

                r += 1
                ttk.Label(displayContent, text='Last Network Comms:  ', font=fontleft, justify='right'
                    #, relief='solid', borderwidth=1
                    ).grid(row=r, column=0, sticky='ne')
                netStatusLocs=[{'parent':displayContent,'row':r,'column':1}]

                # add network widgets to popup
                self.erl2context['network'].addWidgets(
                                                       typeLocs=typeLocs,
                                                       nameLocs=nameLocs,
                                                       interfaceLocs=interfaceLocs,
                                                       ipLocs=ipLocs,
                                                       macLocs=macLocs,
                                                       statusLocs=netStatusLocs,
                                                       )

        # the 'Settings' popup...
        elif Erl2Popup.popupType == 'Settings':

            # these controls are defined in the startup module
            if ('startup' in self.erl2context):

                # add a control to set / unset fullscreen mode
                r += 1
                self.erl2context['startup'].createFullscreenWidget(widgetLoc={'parent':displayContent,'row':r})

                # add a control to enable / disable the Erl2NumPad popups
                r += 1
                self.erl2context['startup'].createNumPadWidget(widgetLoc={'parent':displayContent,'row':r})

        # the 'Network' popup...
        elif Erl2Popup.popupType == 'Network':

            # this item is only relevant if network is defined
            if 'network' in self.erl2context and self.erl2context['network'] is not None:

                r += 1
                childrenLocs=[{'parent':displayContent,'row':r}]

                # add network widgets to popup
                self.erl2context['network'].addWidgets(childrenLocs=childrenLocs)

        for row in range(r-1):
            displayContent.rowconfigure(row,weight=0)
        displayContent.rowconfigure(r,weight=1)
        displayContent.columnconfigure(0,weight=1)
        displayContent.columnconfigure(1,weight=1)

        # buttons row
        c = -1

        # left padding
        c += 1
        ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1
        ).grid(row=0, column=c, padx='0', pady=0, sticky='ew')

        # if this is the 'Network' popup, add the Rescan button
        if Erl2Popup.popupType == 'Network':
            c += 1
            self.erl2context['network'].addWidgets(buttonLocs=[{'parent':displayButtons, 'padding':'2 2', 'relief':'solid', 'borderwidth':1,
                                                                'row':0, 'column':c, 'padx':'0 4', 'pady':'0', 'sticky':'ew'}])

        # exit button
        c += 1
        exitFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        exitFrame.grid(row=0, column=c, padx='0', pady=0, sticky='ew')
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

        exitFrame.rowconfigure(0,weight=1)
        exitFrame.columnconfigure(0,weight=0)
        exitFrame.columnconfigure(1,weight=1)

        # right padding
        c += 1
        ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1
        ).grid(row=0, column=c, padx='0', pady=0, sticky='ew')

        displayButtons.rowconfigure(0,weight=0)
        displayButtons.columnconfigure(0,weight=1)
        for col in range(1,c):
            displayButtons.columnconfigure(col,weight=0)
        displayButtons.columnconfigure(c,weight=1)

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
        if mb.askyesno('Debug Confirmation Window',f"Are you sure you want to close the {Erl2Popup.popupType} window?",parent=self):
            self.destroy()

        self.modalOpen = False
        #self.grab_set()
        #self.transient(self.erl2context['root'])
        #self.onFocusOut()

    # rather than instantiate a new Erl2Popup instance, and risk opening multiple
    # popups at once, provide this classmethod that reads a class attribute and
    # decides whether to instantiate anything (or just co-opt an already-open popup)

    @classmethod
    def openPopup(cls,
                  popupType='About ERL2',
                  erl2context={}):

        if (cls.erl2Popup is not None and cls.erl2Popup.winfo_exists()
                and cls.popupType is not None and cls.popupType == popupType):
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): popup already open")
            cls.erl2Popup.lift()
        else:
            #print (f"{__name__}: Debug: openPopup({cls.__name__}): new popup")
            cls.popupType = popupType
            cls.erl2Popup = Erl2Popup(erl2context=erl2context)

def testPopup(erl2context={}):

    Erl2Popup.openPopup(erl2context=erl2context)

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Popup',font='Arial 30 bold').grid(row=0,column=0)
    b = tk.Button(root,
                  text='Click Here',
                  command=lambda: testPopup(erl2context={'root':root}),
                  )
    b.grid(row=2,column=0)

    root.mainloop()

if __name__ == "__main__": main()

