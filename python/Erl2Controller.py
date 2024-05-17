from multiprocessing import Queue
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2About import Erl2About
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2Network import Erl2Network
from Erl2Readout import Erl2Readout

class Erl2Controller():

    def __init__(self, parent=None, erl2context={}):
        self.parent = parent
        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # pop up a warning message if called directly
        if self.parent is None:
            if not mb.askyesno('Warning',
                               'You have started up the Erl2Controller module directly,'
                               ' which is deprecated in favor of using the newer'
                               ' ErlStartup module. Are you sure you wish to do this?',
                               parent=self.erl2context['root']):
                sys.exit()

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load some images that will be useful later on
        self.erl2context['img'].addImage('network','network-25.png')
        self.erl2context['img'].addImage('settings','settings-25.png')
        self.erl2context['img'].addImage('about','about-25.png')

        # start a system log
        self.__systemLog = Erl2Log(logType='device', logName='Erl2Controller', erl2context=self.erl2context)

        # keep track of when the next file-writing interval is
        self.__nextFileTime = None

        # read these useful parameters from Erl2Config
        self.__deviceType = self.erl2context['conf']['device']['type']
        self.__id = self.erl2context['conf']['device']['id']
        self.__controllerIP = self.erl2context['conf']['network']['controllerIP']
        self.__ipNetworkStub = self.erl2context['conf']['network']['ipNetworkStub']
        self.__ipRange = self.erl2context['conf']['network']['ipRange']
        self.__updateFrequency = self.erl2context['conf']['network']['updateFrequency']

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # remember if network module is active
        self.network = None

        # keep track of devices already encountered and their readout frames
        self.__deviceLabels = []
        self.__deviceReadouts = []

        # divide the main display vertically
        displayTop = ttk.Frame(self.erl2context['root'], padding='2', relief='solid', borderwidth=1)
        displayTop.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        displayBody = ttk.Frame(self.erl2context['root'], padding='0', relief='solid', borderwidth=0)
        displayBody.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')

        # divide the displayBody into top (tanks) and bottom (buttons) sections
        self.__displayTanks = ttk.Frame(displayBody, padding='2', relief='solid', borderwidth=1)
        self.__displayTanks.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        #displaySettings = ttk.Frame(displayBody, padding='2', relief='solid', borderwidth=1)
        #displaySettings.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')
        displayButtons = ttk.Frame(displayBody, padding='0', relief='flat', borderwidth=0)
        displayButtons.grid(row=2, column=0, padx='2', pady='2', sticky='nesw')

        # add frames to allWidgets array for widgetless modules add use .after() methods
        self.erl2context['conf']['system']['allWidgets'].append(displayTop)
        self.erl2context['conf']['system']['allWidgets'].append(displayBody)
        self.erl2context['conf']['system']['allWidgets'].append(displayButtons)
        #print (f"{self.__class__.__name__}: Debug: allWidgets length [{len(self.erl2context['conf']['system']['allWidgets'])}]")

        ## create subframes for settings: network, controls, power, about
        #displayNetwork = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        #displayNetwork.grid(row=1, column=0, columnspan=2, padx='2', pady='2', sticky='nesw')
        #displayControls = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        #displayControls.grid(row=2, column=0, padx='2', pady='2', sticky='nesw')
        ##displayPower = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        ##displayPower.grid(row=3, column=0, padx='2', pady='2', sticky='nesw')
        #displayAbout = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        #displayAbout.grid(row=2, column=1, rowspan=2, padx='2', pady='2', sticky='nesw')

        # create a header frame and put a label in it for now
        header = ttk.Frame(displayTop, padding='2', relief='solid', borderwidth=0)
        header.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        ttk.Label(header,text='Erl2Controller',font='Arial 30 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0,column=0,columnspan=2)

        # add a clock widget in the upper right corner
        clock = Erl2Clock(clockLoc={'parent':displayTop,'row':0,'column':1,'sticky':'e'},
                          erl2context=self.erl2context)

        ## labels for the frames in displayBody
        #ttk.Label(self.__displayTanks, text='Tanks', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')
        #ttk.Label(displaySettings, text='Settings', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')
        #ttk.Label(displayButtons, text='Buttons', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')

        ## labels for the frames in displaySettings
        #ttk.Label(displayNetwork, text='Network', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')
        #ttk.Label(displayControls, text='Controls', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')
        #ttk.Label(displayPower, text='Power', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')
        #ttk.Label(displayAbout, text='About ERL2', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')

        # set up all the relative Frame weights

        # root has Top and Body (Body given weight)
        self.erl2context['root'].rowconfigure(0,weight=0)
        self.erl2context['root'].rowconfigure(1,weight=1)
        self.erl2context['root'].columnconfigure(0,weight=1)

        # displayTop has the header/title and clock (header/title given weight)
        displayTop.rowconfigure(0,weight=1)
        displayTop.columnconfigure(0,weight=1)
        displayTop.columnconfigure(1,weight=0)

        # displayBody has tanks and settings (tanks given weight)
        displayBody.rowconfigure(0,weight=1)
        displayBody.rowconfigure(1,weight=0)
        displayBody.rowconfigure(2,weight=0)
        displayBody.columnconfigure(0,weight=1)

        ## displaySettings has network, controls, power and about
        ## (network + controls have vertical weight, about has horizontal weight)
        #displaySettings.rowconfigure(0,weight=0)
        #displaySettings.rowconfigure(1,weight=1)
        #displaySettings.rowconfigure(2,weight=1)
        #displaySettings.rowconfigure(3,weight=0)
        #displaySettings.columnconfigure(0,weight=0)
        #displaySettings.columnconfigure(1,weight=1)

        ## these controls are defined in the parent module
        #if (self.parent is not None):

        #    # add a control to set / unset fullscreen mode
        #    r = 1
        #    self.parent.createFullscreenWidget(widgetLoc={'parent':displayControls,'row':r})

        #    # add a control to enable / disable the Erl2NumPad popups
        #    r += 1
        #    self.parent.createNumPadWidget(widgetLoc={'parent':displayControls,'row':r})

        #    r += 1
        #    rescanLoc={'parent':displayControls,'row':r,'column':0}

        # buttons frame contents (at bottom)
        c = -1

        # placeholder buttons for now

        # network details
        c += 1
        networkFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        networkFrame.grid(row=0, column=c, padx='0 4', pady=0, sticky='ew')
        networkButton = tk.Button(networkFrame,
                                  image=self.erl2context['img']['network'],
                                  height=40,
                                  width=40,
                                  bd=0,
                                  highlightthickness=0,
                                  activebackground='#DBDBDB',
                                  command=self.dummy)
        networkButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(networkFrame, text='Network', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.dummy)

        networkFrame.rowconfigure(0,weight=1)
        networkFrame.columnconfigure(0,weight=0)
        networkFrame.columnconfigure(1,weight=1)

        # settings
        c += 1
        settingsFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        settingsFrame.grid(row=0, column=c, padx='0 4', pady=0, sticky='ew')
        settingsButton = tk.Button(settingsFrame,
                                   image=self.erl2context['img']['settings'],
                                   height=40,
                                   width=40,
                                   bd=0,
                                   highlightthickness=0,
                                   activebackground='#DBDBDB',
                                   command=self.dummy)
        settingsButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(settingsFrame, text='Settings', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.dummy)

        settingsFrame.rowconfigure(0,weight=1)
        settingsFrame.columnconfigure(0,weight=0)
        settingsFrame.columnconfigure(1,weight=1)

        # about ERL2
        c += 1
        aboutFrame = ttk.Frame(displayButtons, padding='2 2', relief='solid', borderwidth=1)
        aboutFrame.grid(row=0, column=c, padx='0 4', pady=0, sticky='ew')
        aboutButton = tk.Button(aboutFrame,
                                image=self.erl2context['img']['about'],
                                height=40,
                                width=40,
                                bd=0,
                                highlightthickness=0,
                                activebackground='#DBDBDB',
                                command=self.aboutPopup)
        aboutButton.grid(row=0, column=0, padx='2 2', sticky='w')
        l = ttk.Label(aboutFrame, text='About', font='Arial 16'
            #, relief='solid', borderwidth=1
            )
        l.grid(row=0, column=1, padx='2 2', sticky='w')
        l.bind('<Button-1>', self.aboutPopup)

        aboutFrame.rowconfigure(0,weight=1)
        aboutFrame.columnconfigure(0,weight=0)
        aboutFrame.columnconfigure(1,weight=1)

        # these controls are defined in the parent module
        if (self.parent is not None):

            # add a control to restart the app
            c += 1
            self.parent.createRestartWidget(widgetLoc={'parent':displayButtons,'row':0,'column':c,'relief':'solid','borderwidth':1,'padx':'0 4','pady':0},
                                            widgetText='Restart',
                                            )

            # kill the app completely with this shutdown button
            c += 1
            self.parent.createExitWidget(widgetLoc={'parent':displayButtons,'row':0,'column':c,'relief':'solid','borderwidth':1,'padx':0,'pady':0},
                                         widgetText='Shutdown',
                                         )

        ## information about this ERL2 system
        #fontleft = 'Arial 14 bold'
        #fontright = 'Arial 14'

        #r = 1
        #ttk.Label(displayAbout, text='ERL2 Version:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #ttk.Label(displayAbout, text=self.erl2context['conf']['system']['version'], font=fontright
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=1, sticky='nw')

        #r += 1
        #ttk.Label(displayAbout, text='Device Id:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #ttk.Label(displayAbout, text=self.erl2context['conf']['device']['id'], font=fontright
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=1, sticky='nw')

        #r += 1
        #ttk.Label(displayAbout, text='Log Directory:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #ttk.Label(displayAbout, text=self.erl2context['conf']['system']['logDir'], font=fontright
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=1, sticky='nw')

        #r += 1
        #ttk.Label(displayAbout, text='Logging Frequency:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')

        ## elegant way to summarize logging frequency info
        #freq = {}
        #for sens in ['system']:
        #    if self.erl2context['conf'][sens]['loggingFrequency'] not in freq:
        #        freq[self.erl2context['conf'][sens]['loggingFrequency']] = [sens]
        #    else:
        #        freq[self.erl2context['conf'][sens]['loggingFrequency']].append(sens)
        #if len(freq) == 1:
        #    txt = str(self.erl2context['conf']['system']['loggingFrequency']) + ' seconds'
        #else:
        #    txt = ""
        #    num = 0
        #    for k, v in sorted(freq.items(), key=lambda item: len(item[1])):
        #        num += 1
        #        if num < len(freq):
        #            txt += f"{', '.join(v)}: {k} seconds; "
        #        else:
        #            txt += f"other sensors: {k} seconds"

        #ttk.Label(displayAbout, text=txt, font=fontright, wraplength=300
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=1, sticky='nw')

        #r += 1
        #ttk.Label(displayAbout, text='System Startup:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #ttk.Label(displayAbout, text=self.erl2context['conf']['system']['startup'].astimezone(self.erl2context['conf']['system']['timezone']).strftime(self.erl2context['conf']['system']['dtFormat']), font=fontright
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=1, sticky='nw')

        #r += 1
        #ttk.Label(displayAbout, text='System Timezone:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #ttk.Label(displayAbout, text=str(self.erl2context['conf']['system']['timezone']), font=fontright
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=1, sticky='nw')

        #r += 1
        #ttk.Label(displayAbout, text='IP Address:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #ipLocs=[{'parent':displayAbout,'row':r,'column':1}]

        #r += 1
        #ttk.Label(displayAbout, text='MAC Address:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #macLocs=[{'parent':displayAbout,'row':r,'column':1}]

        #r += 1
        #ttk.Label(displayAbout, text='Last Network Comms:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #netStatusLocs=[{'parent':displayAbout,'row':r,'column':1}]

        ## dummy row at end
        #r += 1
        #ttk.Label(displayAbout, text='this space intentionally left blank', font='Arial 12'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, columnspan=2, sticky='s')

        #for row in range(r-1):
        #    displayAbout.rowconfigure(row,weight=0)
        #displayAbout.rowconfigure(r,weight=1)
        #displayAbout.columnconfigure(0,weight=1)
        #displayAbout.columnconfigure(1,weight=1)

        # the logic that enables tank networking, if enabled
        if self.erl2context['conf']['network']['enabled']:

            # don't do this if Erl2Controller was called directly
            if self.parent is not None:
                self.network = Erl2Network(#ipLocs=ipLocs,
                                           #macLocs=macLocs,
                                           #childrenLocs=[{'parent':displayNetwork,'row':1,'column':0,'columnspan':2}],
                                           #buttonLoc=rescanLoc,
                                           erl2context=self.erl2context,
                                          )

        # start up the main processing routine to manage child devices and update displays
        self.updateDisplays()

    def updateDisplays(self):

        # loop through child devices
        tankNum = 0
        for mac in self.network.sortedMacs:

            overwrite = False
            thisID = self.network.childrenDict[mac]['id']

            # label missing? create it
            if len(self.__deviceLabels) < (tankNum+1):

                # draw new label
                l = ttk.Label(self.__displayTanks, text='--', font='Arial 12 bold'
                    #, relief='solid', borderwidth=1
                    )
                l.grid(row=2*tankNum, column=0, sticky='nw')
                self.__deviceLabels.append(l)
                overwrite = True

            # no readout frame yet? create it
            if len(self.__deviceReadouts) < (tankNum+1):
                f = ttk.Frame(self.__displayTanks, padding='0', relief='flat', borderwidth=0)
                f.grid(row=2*tankNum+1, column=0, padx='0', pady='0', sticky='nesw')
                self.__deviceReadouts.append(f)
                overwrite = True

            # something weird is going on if these lists aren't the same size
            assert len(self.__deviceLabels) == len(self.__deviceReadouts)

            # has the count or ordering of devices changed?
            if self.__deviceLabels[tankNum]['text'] != thisID:
                overwrite = True

            # make readout changes if necessary
            if overwrite:

                # update the label text
                self.__deviceLabels[tankNum].config(text=thisID)

                # create readout
                rd = Erl2Readout(deviceState=self.network.childrenStates[mac],
                                 displayLoc={'parent':self.__deviceReadouts[tankNum],'row':0,'column':0},
                                 erl2context=self.erl2context,
                                 )

                # tell Erl2Network what Erl2Readouts are associated with this mac
                if self.network is not None and hasattr(self.network, 'childrenReadouts'):
                    self.network.childrenReadouts[mac] = rd

            # increment before continuing through the loop
            tankNum += 1

        # set up the next call to this method (wait 30s)
        self.__displayTanks.after(30000, self.updateDisplays)

    def aboutPopup(self, event=None):

        #Erl2About.openPopup(erl2context=self.erl2context)
        thing1 = Erl2About(erl2context=self.erl2context)
        self.erl2context['root'].wait_window(thing1)

    def dummy(self):
        pass

    # for a graceful shutdown
    def gracefulExit(self):

        # set any controls to zero
        if hasattr(self, 'controls'):
            for c in self.controls.values():
                c.setControl(0,force=True)

        # terminate subthreads in network module
        if self.network is not None:
            self.network.atexitHandler()

def main():

    root = tk.Tk()
    root.rowconfigure(0,weight=1)
    root.columnconfigure(0,weight=1)
    controller = Erl2Controller({'root':root})

    root.mainloop()

if __name__ == "__main__": main()

