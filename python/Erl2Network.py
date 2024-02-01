import atexit
from datetime import datetime as dt
from datetime import timezone as tz
from multiprocessing import Process,Queue
import netifaces
import pickle
import re
import selectors
import socket
import tkinter as tk
import types
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image

class Erl2Network():

    # port to communicate on
    PORT = 65432

    def __init__(self,
                 typeLocs=[],
                 interfaceLocs=[],
                 ipLocs=[],
                 macLocs=[],
                 statusLocs=[],
                 childrenLocs=[],
                 erl2context={}):

        self.__typeLocs = typeLocs
        self.__interfaceLocs = interfaceLocs
        self.__ipLocs = ipLocs
        self.__macLocs = macLocs
        self.__statusLocs = statusLocs
        self.__childrenLocs = childrenLocs
        self.erl2context = erl2context

        # remember what widgets are active for this sensor
        self.__typeWidgets = []
        self.__interfaceWidgets = []
        self.__ipWidgets = []
        self.__macWidgets = []
        self.__statusWidgets = []
        self.__childrenWidgets = []

        # if multithreading, remember what process is running
        self.__process = None
        self.__statusQueue = Queue()
        self.__lastActive = None

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__type = self.erl2context['conf']['device']['type']
        self.__id = self.erl2context['conf']['device']['id']
        self.__ipNetworkStub = self.erl2context['conf']['network']['ipNetworkStub']
        self.__ipRange = self.erl2context['conf']['network']['ipRange']
        self.__updateFrequency = self.erl2context['conf']['network']['updateFrequency']

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load this image that may be needed for Erl2Network controls
        self.erl2context['img'].addImage('rescan','network-25.png')

        # details of the network connection(s)
        self.__tankAddresses = []
        self.__networkStubs = []

        # status attributes of this network connection
        self.__interface = None
        self.__ip = None
        self.__mac = None
        self.__children = {}

        # selector
        self.__sel = selectors.DefaultSelector()

        # start by creating the display widgets
        self.createDisplayWidgets('type')
        self.createDisplayWidgets('interface')
        self.createDisplayWidgets('ip')
        self.createDisplayWidgets('mac')
        self.createDisplayWidgets('status')

        # determine what IP address(es) to use
        self.getAddresses()

        print (f"{self.__class__.__name__}: Debug: __init: self.__tankAddresses is [{self.__tankAddresses}]")
        print (f"{self.__class__.__name__}: Debug: __init: self.__networkStubs is [{self.__networkStubs}]")

        # if controller, start scanning for tanks
        if self.__type == 'controller':

            # populate the display fields with controller-type details
            self.__interface = self.__networkStubs[0]['IF']
            self.__ip = self.__networkStubs[0]['IP']
            self.__mac = self.__networkStubs[0]['MAC']

            self.updateDisplayWidgets()

            # do this in a separate process thread
            self.__process = Process(target=self.tankScan, args=(self.__statusQueue,))
            self.__process.start()

            #self.tankScan(self.__statusQueue)

        # if tank, listen for connections from controller
        elif self.__type == 'tank':

            # populate the display fields with controller-type details
            self.__interface = self.__tankAddresses[0]['IF']
            self.__ip = self.__tankAddresses[0]['IP']
            self.__mac = self.__tankAddresses[0]['MAC']

            self.updateDisplayWidgets()

            # do this in a separate process thread
            self.__process = Process(target=self.listen, args=(self.__statusQueue,))
            self.__process.start()

            #self.listen()

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print (f"{self.__class__.__name__}: Debug: Accepted connection from {addr}")
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.__sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                #data.outb += recv_data
                print (f"{self.__class__.__name__}: Debug: Received data {recv_data}")
                if recv_data == b"ID":
                    data.outb = f"{self.__type}|{self.__id}|{self.__tankAddresses[0]['MAC']}".encode()
                elif recv_data == b"TIME":
                    t = dt.now(tz=tz.utc)
                    #data.outb = f"{t.astimezone(self.__timezone).strftime(self.__dtFormat)}".encode()
                    data.outb = pickle.dumps(t)
            else:
                print (f"{self.__class__.__name__}: Debug: Closing connection to {data.addr}")
                self.__sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                print (f"{self.__class__.__name__}: Debug: Echoing {data.outb!r} to {data.addr}")
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def getAddresses(self):

        # reset lists
        self.__tankAddresses = []
        self.__networkStubs = []

        # come up with a list of all possible IPv4 interface addresses
        for i in netifaces.interfaces():

            # this is a dict of address types; AF_INET is IPv4
            ifList = netifaces.ifaddresses(i)
            if netifaces.AF_INET in ifList.keys():

                # this is a list of address dicts (can be more than one IP per hw interface)
                for adr in ifList[netifaces.AF_INET]:

                    # only check dicts with 'addr' key
                    if 'addr' in adr.keys():

                        # skip loopback/localhost address; skip Automatic Private IP Addresses (APIPA)
                        if adr['addr'] != '127.0.0.1' and re.search('^169\.254\.',adr['addr']) is None:

                            # figure out any associated MAC address
                            mac = None
                            if netifaces.AF_LINK in ifList.keys() and len(ifList[netifaces.AF_LINK]) > 0 and 'addr' in ifList[netifaces.AF_LINK][0]:
                                mac = ifList[netifaces.AF_LINK][0]['addr']

                            # addresses that already end in .1 represent networks that
                            # a controller can scan for tanks
                            if re.search('\.1$',adr['addr']) is not None:
                                # strip off the 1 and save the network stub
                                self.__networkStubs.append({'IF':i, 'IP':adr['addr'], 'MAC':mac, 'STUB':re.sub('\.1$','.',adr['addr'])})

                            # addresses that don't end in .1 are interfaces that
                            # a tank can listen on for connections from a controller
                            else:
                                self.__tankAddresses.append({'IF':i, 'IP':adr['addr'], 'MAC':mac})

    def tankScan(self, statusQ):

        # scan all stubs
        for stub in self.__networkStubs:
            # for now, just test .2 through .63
            for addr in range(2,64):
                host = stub['STUB'] + str(addr)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.settimeout(.5)
                        ret = s.connect_ex((host, self.PORT))
                        if ret == 0:
                            t = dt.now(tz=tz.utc)
                            print (f"{self.__class__.__name__}: Debug: tankScan: adding [{t}] to statusQ")
                            statusQ.put(t)
                            print (f"{self.__class__.__name__}: Debug: Successfully connected to [{host}] from [{stub['IF']}][{stub['IP']}][{stub['MAC']}]")

                            print (f"{self.__class__.__name__}: Debug: Sending [ID]")
                            s.sendall(b"ID")
                            data = s.recv(1024)
                            print (f"{self.__class__.__name__}: Debug: Received reply: [{data}]")

                            print (f"{self.__class__.__name__}: Debug: Sending [TIME]")
                            s.sendall(b"TIME")
                            data = s.recv(1024)
                            #print (f"{self.__class__.__name__}: Debug: Received reply: [{data}]")
                            t = pickle.loads(data)
                            print (f"{self.__class__.__name__}: Debug: Received reply: [{t}]")
                            print (f"{self.__class__.__name__}: Debug: Local time is : [{dt.now(tz=tz.utc)}]")

                        else:
                            print (f"{self.__class__.__name__}: Debug: Cannot connect to [{host}] from [{stub['IF']}][{stub['IP']}][{stub['MAC']}]: ret [{ret}]")
                    except Exception as e:
                        print (f"{self.__class__.__name__}: Error: unexpected error when connecting to [{host}] from [{stub['IF']}][{stub['IP']}][{stub['MAC']}]: [{e}]")
                    finally:
                        s.close()

    def listen(self, statusQ):

        print (f"{self.__class__.__name__}: Debug: tank listening on address [{self.__tankAddresses[0]['IF']}][{self.__tankAddresses[0]['IP']}][{self.__tankAddresses[0]['MAC']}], port [{self.PORT}]")

        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.__tankAddresses[0]['IP'], self.PORT))
        lsock.listen()
        print (f"{self.__class__.__name__}: Debug: Listening on {(self.__tankAddresses[0]['IP'], self.PORT)}")
        lsock.setblocking(False)
        self.__sel.register(lsock, selectors.EVENT_READ, data=None)

        try:
            while True:
                events = self.__sel.select(timeout=None)
                t = dt.now(tz=tz.utc)
                print (f"{self.__class__.__name__}: Debug: listen: adding [{t}] to statusQ")
                statusQ.put(t)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        self.service_connection(key, mask)
        except KeyboardInterrupt:
            print (f"{self.__class__.__name__}: Debug: Caught keyboard interrupt, exiting")
        finally:
            self.__sel.close()

    def createDisplayWidgets(self, displayType):

        # reuse this method for all the different display fields
        if displayType == 'type': locations = self.__typeLocs
        elif displayType == 'interface': locations = self.__interfaceLocs
        elif displayType == 'ip': locations = self.__ipLocs
        elif displayType == 'mac': locations = self.__macLocs
        elif displayType == 'status': locations = self.__statusLocs

        for loc in locations:

            # create the display widget's base frame as a child of its parent
            f = ttk.Frame(loc['parent'], padding='0 0', relief='flat', borderwidth=0)
            f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nw')

            # add a Label widget to show the current sensor value
            l = ttk.Label(f, text='--', font='Arial 16', foreground='#1C4587')
            l.grid(row=0, column=0, sticky='nw')

            # keep a list of status widgets for this sensor
            if displayType == 'type': self.__typeWidgets.append(l)
            elif displayType == 'interface': self.__interfaceWidgets.append(l)
            elif displayType == 'ip': self.__ipWidgets.append(l)
            elif displayType == 'mac': self.__macWidgets.append(l)
            elif displayType == 'status': self.__statusWidgets.append(l)

    def updateDisplayWidgets(self, scheduleNext=True):

        # current time
        currentTime = dt.now(tz=tz.utc)

        # default formatting
        fnt = 'Arial 14'
        fgd = '#1C4587'

        # loop through all placements of the type widgets
        for w in self.__typeWidgets:

            # set the update value
            if self.__type is None: upd = '--'
            else: upd = self.__type

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)
 
        # loop through all placements of the interface widgets
        for w in self.__interfaceWidgets:

            # set the update value
            if self.__interface is None: upd = '--'
            else: upd = self.__interface

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)
 
        # loop through all placements of the ip widgets
        for w in self.__ipWidgets:

            # set the update value
            if self.__ip is None: upd = '--'
            else: upd = self.__ip

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)
 
        # loop through all placements of the mac widgets
        for w in self.__macWidgets:

            # set the update value
            if self.__mac is None: upd = '--'
            else: upd = self.__mac

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)

        # figure out when the last network activity was
        while not self.__statusQueue.empty():
            self.__lastActive = self.__statusQueue.get_nowait()
            print (f"{self.__class__.__name__}: updateDisplayWidgets: retrieved [{self.__lastActive}] from statusQ")
 
        # set the update value
        if self.__lastActive is None: upd = 'never'
        else: upd = self.__lastActive.astimezone(self.__timezone).strftime(self.__dtFormat)

        # adjust the formatting if the communications have gone quiet
        if self.__lastActive is None or currentTime.timestamp() - self.__lastActive.timestamp() > 300:
            fnt = 'Arial 14 bold'
            fgd = '#A93226'
        else:
            fnt = 'Arial 14'
            fgd = '#1C4587'

        # loop through all placements of the status widgets
        for w in self.__statusWidgets:

            # update the display
            w.config(text=upd,font=fnt,foreground=fgd)

        # if asked to, schedule the next display update
        if scheduleNext:

            # update on schedule
            delay = (int(
                      (
                        (
                          int(
                            currentTime.timestamp()  # timestamp in seconds
                            / self.__updateFrequency # convert to number of intervals of length updateFrequency
                          )                          # truncate to beginning of previous interval (past)
                        + 1)                         # advance by one time interval (future)
                        * self.__updateFrequency     # convert back to seconds/timestamp
                        - currentTime.timestamp()    # calculate how many seconds from now to next interval
                        )
                      * 1000)                        # convert to milliseconds, then truncate to integer
                    ) 
        
            # update the display widgets again after waiting an appropriate number of milliseconds
            self.__ipWidgets[0].after(delay, self.updateDisplayWidgets)
 
    # atexit.register() handler
    def atexitHandler(self):

        #print (f"{self.__class__.__name__}: Debug: atexitHandler() called")
    
        # kill off the forked process listening for connections
        if self.__process is not None and self.__process.is_alive():
            self.__process.kill()

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Network',font='Arial 30 bold').grid(row=0,column=0,columnspan=2)

    ttk.Label(root,text='Type:',font='Arial 14 bold',justify='right').grid(row=1,column=0,sticky='nse')
    ttk.Label(root,text='Network interface:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nse')
    ttk.Label(root,text='IP address:',font='Arial 14 bold',justify='right').grid(row=3,column=0,sticky='nse')
    ttk.Label(root,text='MAC address:',font='Arial 14 bold',justify='right').grid(row=4,column=0,sticky='nse')
    ttk.Label(root,text='Last network comms:',font='Arial 14 bold',justify='right').grid(row=5,column=0,sticky='nse')

    childrenFrame = ttk.Frame(root)
    childrenFrame.grid(row=6,column=0,columnspan=2)

    network = Erl2Network(typeLocs=[{'parent':root,'row':1,'column':1}],
                          interfaceLocs=[{'parent':root,'row':2,'column':1}],
                          ipLocs=[{'parent':root,'row':3,'column':1}],
                          macLocs=[{'parent':root,'row':4,'column':1}],
                          statusLocs=[{'parent':root,'row':5,'column':1}],
                          childrenLocs=[{'parent':childrenFrame,'row':0,'column':0}])

    # set things up for graceful termination
    atexit.register(network.atexitHandler)

    root.mainloop()

if __name__ == "__main__": main()

