from multiprocessing import Queue
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Clock import Erl2Clock
from Erl2Config import Erl2Config
from Erl2Log import Erl2Log
from Erl2Network import Erl2Network

class Erl2Controller():

    def __init__(self, root, parent=None, erl2context={}):
        self.root = root
        self.parent = parent
        self.erl2context = erl2context

        # pop up a warning message if called directly
        if self.parent is None:
            if not mb.askyesno('Warning','You have started up the Erl2Controller module directly,'
                                         ' which is deprecated in favor of using the newer'
                                         ' ErlStartup module. Are you sure you wish to do this?'):
                sys.exit()

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

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

        # the heart of this module is its list of child devices
        self.__masterList = {}

        # remember if network module is active
        self.network = None

        # if necessary, create an object to hold/remember image objects
        #if 'img' not in self.erl2context:
        #    self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load this image that may be needed for Erl2Controller controls
        #self.erl2context['img'].addImage('rescan', 'network-25.png')

        # divide the main display vertically
        displayTop = ttk.Frame(root, padding='2', relief='solid', borderwidth=1)
        displayTop.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        displayBody = ttk.Frame(root, padding='0', relief='solid', borderwidth=0)
        displayBody.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')

        # divide the displayBody into left (tanks) and right (settings) sides
        self.__displayTanks = ttk.Frame(displayBody, padding='2', relief='solid', borderwidth=1)
        self.__displayTanks.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        displaySettings = ttk.Frame(displayBody, padding='0', relief='solid', borderwidth=0)
        displaySettings.grid(row=0, column=1, padx='2', pady='2', sticky='nesw')

        # create subframes for settings: network, controls, power, about
        #displayNetwork = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        #displayNetwork.grid(row=0, column=0, columnspan=2, padx='2', pady='2', sticky='nesw')
        displayControls = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        displayControls.grid(row=1, column=0, padx='2', pady='2', sticky='nesw')
        displayPower = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        displayPower.grid(row=2, column=0, padx='2', pady='2', sticky='nesw')
        displayAbout = ttk.Frame(displaySettings, padding='2', relief='solid', borderwidth=1)
        displayAbout.grid(row=1, column=1, rowspan=2, padx='2', pady='2', sticky='nesw')

        # create a header frame and put a label in it for now
        header = ttk.Frame(displayTop, padding='2', relief='solid', borderwidth=0)
        header.grid(row=0, column=0, padx='2', pady='2', sticky='nesw')
        ttk.Label(header,text='Erl2Controller',font='Arial 30 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0,column=0,columnspan=2)

        # add a clock widget in the upper right corner
        clock = Erl2Clock(clockLoc={'parent':displayTop,'row':0,'column':1,'sticky':'e'},
                          erl2context=self.erl2context)

        # labels for the frames in displayBody
        ttk.Label(self.__displayTanks, text='Tanks', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        #ttk.Label(displaySettings, text='Settings', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')

        # labels for the frames in displaySettings
        #ttk.Label(displayNetwork, text='Network', font='Arial 12 bold'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=0, column=0, sticky='nw')
        ttk.Label(displayControls, text='Controls', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(displayPower, text='Power', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')
        ttk.Label(displayAbout, text='About ERL2', font='Arial 12 bold'
            #, relief='solid', borderwidth=1
            ).grid(row=0, column=0, sticky='nw')

        # set up all the relative Frame weights

        # root has Top and Body (Body given weight)
        root.rowconfigure(0,weight=0)
        root.rowconfigure(1,weight=1)
        root.columnconfigure(0,weight=1)

        # displayTop has the header/title and clock (header/title given weight)
        displayTop.rowconfigure(0,weight=1)
        displayTop.columnconfigure(0,weight=1)
        displayTop.columnconfigure(1,weight=0)

        # displayBody has tanks and settings (tanks given weight)
        displayBody.rowconfigure(0,weight=1)
        displayBody.columnconfigure(0,weight=1)
        displayBody.columnconfigure(1,weight=0)

        # displaySettings has network, controls, power and about
        # (network + controls have vertical weight, about has horizontal weight)
        displaySettings.rowconfigure(0,weight=1)
        displaySettings.rowconfigure(1,weight=1)
        displaySettings.rowconfigure(2,weight=0)
        displaySettings.columnconfigure(0,weight=0)
        displaySettings.columnconfigure(1,weight=1)

        # these controls are defined in the parent module
        if (self.parent is not None):

            # add a control to set / unset fullscreen mode
            r = 1
            self.parent.createFullscreenWidget(loc={'parent':displayControls,'row':r})

            # add a control to enable / disable the Erl2NumPad popups
            r += 1
            self.parent.createNumPadWidget(loc={'parent':displayControls,'row':r})

            r += 1
            rescanLoc={'parent':displayControls,'row':r,'column':0}

            # add a control to restart the app
            r = 1
            self.parent.createRestartWidget(loc={'parent':displayPower,'row':r})

            # kill the app completely with this shutdown button
            r += 1
            self.parent.createExitWidget(loc={'parent':displayPower,'row':r})

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

        #r += 1
        #ttk.Label(displayAbout, text='Last Network Comms:  ', font=fontleft, justify='right'
        #    #, relief='solid', borderwidth=1
        #    ).grid(row=r, column=0, sticky='ne')
        #netStatusLocs=[{'parent':displayAbout,'row':r,'column':1}]

        # dummy row at end
        r += 1
        ttk.Label(displayAbout, text='this space intentionally left blank', font='Arial 12'
            #, relief='solid', borderwidth=1
            ).grid(row=r, column=0, columnspan=2, sticky='s')

        for row in range(r-1):
            displayAbout.rowconfigure(row,weight=0)
        displayAbout.rowconfigure(r,weight=1)
        displayAbout.columnconfigure(0,weight=1)
        displayAbout.columnconfigure(1,weight=1)

        # the logic that enables tank networking, if enabled
        if self.erl2context['conf']['network']['enabled']:

            # don't do this if Erl2Controller was called directly
            if self.parent is not None:
                self.network = Erl2Network(ipLocs=ipLocs,
                                           macLocs=macLocs,
                                           childrenLocs=[{'parent':displaySettings,'row':0,'column':0,'columnspan':2}],
                                           buttonLoc=rescanLoc,
                                           erl2context=self.erl2context,
                                          )

        # start up the main processing routine to manage child devices and update displays
        self.updateDisplays()

    def updateDisplays(self):

        # don't run device updates during a device scan
        if not self.network.scanning():

            # messaging depends on whether we are starting from scratch (startup)
            if len(self.__masterList) == 0: startup = True
            else:                           startup = False

            # loop through currently-networked devices; compare to master list
            for mac in self.network.sortedMacs:

                # get this mac's id
                id = self.network.childrenDict[mac]['id']

                # add to master list if it's not already there
                if id not in self.__masterList:
                    self.__masterList[id] = {'mac':mac}

            # loop through master list
            for id in self.__masterList:

                # get this id's mac
                if 'mac' in self.__masterList[id]: mac = self.__masterList[id]['mac']
                else:                              mac = None

                # set up a reply queue for this request, if needed
                if 'replyQ' not in self.__masterList[id]:
                    self.__masterList[id]['replyQ'] = Queue()

                # get this device's state
                state = self.network.getState(mac, self.__masterList[id]['replyQ'])

            # 1. is the device active? "ID"
            # 2. what is the device's state? "GET.STATE"
            # 3. collect any new data "GET.DATA | YYYYMMDDHHMMSS"

            # 4. update displays -- last comms, state, new data

        # set up the next call to this method (wait 30s)
        self.__displayTanks.after(30000, self.updateDisplays)

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
    controller = Erl2Controller(root)

    root.mainloop()

if __name__ == "__main__": main()

