import atexit
from datetime import datetime as dt
from datetime import timezone as tz
from multiprocessing import Process, Queue
import netifaces
import pickle
import re
import selectors
import socket
import types
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image

# Erl2Network needs some functions defined outside of the class, because
# in macOS and Windows, you cannot start a process in a subthread if it is
# calling a method of a class with complex attributes (like from tkinter)

# The start of the Erl2Network class definition can be found further down

# port to communicate on
PORT = 65432

def acceptWrapper(sel,
                  sock):

    conn, addr = sock.accept()  # Should be ready to read
    print (f"Erl2Network|acceptWrapper: Debug: accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def serviceConnection(deviceType,
                      id,
                      mac,
                      timezone,
                      dtFormat,
                      sel,
                      key,
                      mask):

    sock = key.fileobj
    data = key.data

    if mask & selectors.EVENT_READ:

        recv_data = sock.recv(1024)  # Should be ready to read

        if recv_data:

            print (f"Erl2Network|serviceConnection: Debug: received data {recv_data}")

            if recv_data == b"ID":
                data.outb = '\n'.join([deviceType, id, mac]).encode()

            elif recv_data == b"TIME":
                t = dt.now(tz=tz.utc)
                #data.outb = f"{t.astimezone(timezone).strftime(dtFormat)}".encode()
                data.outb = pickle.dumps(t)
        else:
            print (f"Erl2Network|serviceConnection: Debug: closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()

    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print (f"Erl2Network|serviceConnection: Debug: echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]

def tankScan(deviceType,
             id,
             interface,
             ip,
             mac,
             timezone,
             dtFormat,
             networkStubs,
             statusQ,
             childrenQ):

    # scan all stubs
    for stub in networkStubs:

        # for now, just test .2 through .63
        for addr in range(2,64):

            host = stub['STUB'] + str(addr)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

                try:
                    s.settimeout(.5)
                    ret = s.connect_ex((host, PORT))

                    if ret == 0:
                        t = dt.now(tz=tz.utc)
                        print (f"Erl2Network|tankScan: Debug: adding [{t}] to statusQ")
                        statusQ.put(t)
                        print (f"Erl2Network|tankScan: Debug: successfully connected to [{host}] from [{stub['IF']}][{stub['IP']}][{stub['MAC']}]")

                        print (f"Erl2Network|tankScan: Debug: sending [ID]")
                        s.sendall(b"ID")
                        data = s.recv(1024)
                        print (f"Erl2Network|tankScan: Debug: received reply: [{data}]")
                        val = '\n'.join([data.decode(), host])
                        print (f"Erl2Network|tankScan: Debug: adding [{val}] to childrenQ")
                        childrenQ.put(val)

                        print (f"Erl2Network|tankScan: Debug: sending [TIME]")
                        s.sendall(b"TIME")
                        data = s.recv(1024)
                        #print (f"Erl2Network|tankScan: Debug: received reply: [{data}]")
                        t = pickle.loads(data)
                        print (f"Erl2Network|tankScan: Debug: received reply: [{t}]")
                        print (f"Erl2Network|tankScan: Debug: local time is : [{dt.now(tz=tz.utc)}]")

                    else:
                        pass
                        #print (f"Erl2Network|tankScan: Debug: cannot connect to [{host}] from [{stub['IF']}][{stub['IP']}][{stub['MAC']}]: ret [{ret}]")

                except Exception as e:
                    print (f"Erl2Network|tankScan: Error: unexpected error when connecting to [{host}] from [{stub['IF']}][{stub['IP']}][{stub['MAC']}]: [{e}]")

                finally:
                    s.close()

def listen(deviceType,
           id,
           interface,
           ip,
           mac,
           timezone,
           dtFormat,
           tankAddress,
           statusQ):

    print (f"Erl2Network|listen: Debug: tank listening on address [{interface}][{ip}][{mac}], port [{PORT}]")

    # initialize selector
    sel = selectors.DefaultSelector()

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((tankAddress, PORT))
    lsock.listen()
    print (f"Erl2Network|listen: Debug: listening on {(tankAddress, PORT)}")
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)

    try:
        while True:
            events = sel.select(timeout=None)
            t = dt.now(tz=tz.utc)
            print (f"Erl2Network|listen: Debug: adding [{t}] to statusQ")
            statusQ.put(t)

            for key, mask in events:
                if key.data is None:
                    acceptWrapper(sel, key.fileobj)
                else:
                    serviceConnection(deviceType, id, mac, timezone, dtFormat, sel, key, mask)

    except KeyboardInterrupt:
        print (f"Erl2Network|listen: Debug: caught keyboard interrupt, exiting")

    finally:
        sel.close()

#-----

class Erl2Network():

    # port to communicate on
    PORT = 65432

    def __init__(self,
                 typeLocs=[],
                 nameLocs=[],
                 interfaceLocs=[],
                 ipLocs=[],
                 macLocs=[],
                 statusLocs=[],
                 childrenLocs=[],
                 erl2context={}):

        self.__typeLocs = typeLocs
        self.__nameLocs = nameLocs
        self.__interfaceLocs = interfaceLocs
        self.__ipLocs = ipLocs
        self.__macLocs = macLocs
        self.__statusLocs = statusLocs
        self.__childrenLocs = childrenLocs
        self.erl2context = erl2context

        # remember what widgets are active for this network
        self.__typeWidgets = []
        self.__nameWidgets = []
        self.__interfaceWidgets = []
        self.__ipWidgets = []
        self.__macWidgets = []
        self.__statusWidgets = []
        self.__childrenWidgets = []

        # multithreading: what process is running, queues for sharing data
        self.__process = None
        self.__statusQueue = Queue()
        self.__lastActive = None
        self.__childrenQueue = Queue()
        self.__childrenDict = {}
        self.__newChildren = False

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__deviceType = self.erl2context['conf']['device']['type']
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
        self.erl2context['img'].addImage('rescan', 'network-25.png')

        # details of the network connection(s)
        self.__tankAddresses = []
        self.__networkStubs = []

        # status attributes of this network connection
        self.__interface = None
        self.__ip = None
        self.__mac = None

        # start by creating the display widgets
        self.createDisplayWidgets('type')
        self.createDisplayWidgets('name')
        self.createDisplayWidgets('interface')
        self.createDisplayWidgets('ip')
        self.createDisplayWidgets('mac')
        self.createDisplayWidgets('status')
        self.createDisplayWidgets('children')

        # determine what IP address(es) to use
        self.getAddresses()

        print (f"{self.__class__.__name__}: Debug: __init: self.__tankAddresses is [{self.__tankAddresses}]")
        print (f"{self.__class__.__name__}: Debug: __init: self.__networkStubs is [{self.__networkStubs}]")

        # if controller, start scanning for tanks
        if self.__deviceType == 'controller':

            # populate the display fields with controller-type details
            self.__interface = self.__networkStubs[0]['IF']
            self.__ip = self.__networkStubs[0]['IP']
            self.__mac = self.__networkStubs[0]['MAC']

            self.updateDisplayWidgets()

            # do this in a separate process thread
            self.__process = Process(target=tankScan,
                                     args=(self.__deviceType,
                                           self.__id,
                                           self.__interface,
                                           self.__ip,
                                           self.__mac,
                                           self.__timezone,
                                           self.__dtFormat,
                                           self.__networkStubs,
                                           self.__statusQueue,
                                           self.__childrenQueue, ))
            self.__process.start()

        # if tank, listen for connections from controller
        elif self.__deviceType == 'tank':

            # populate the display fields with controller-type details
            self.__interface = self.__tankAddresses[0]['IF']
            self.__ip = self.__tankAddresses[0]['IP']
            self.__mac = self.__tankAddresses[0]['MAC']

            self.updateDisplayWidgets()

            # do this in a separate process thread
            self.__process = Process(target=listen,
                                     args=(self.__deviceType,
                                           self.__id,
                                           self.__interface,
                                           self.__ip,
                                           self.__mac,
                                           self.__timezone,
                                           self.__dtFormat,
                                           self.__tankAddresses[0]['IP'],
                                           self.__statusQueue, ))
            self.__process.start()

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
                        if adr['addr'] != '127.0.0.1' and re.search('^169\.254\.', adr['addr']) is None:

                            # figure out any associated MAC address
                            mac = None
                            if netifaces.AF_LINK in ifList.keys() and len(ifList[netifaces.AF_LINK]) > 0 and 'addr' in ifList[netifaces.AF_LINK][0]:
                                mac = ifList[netifaces.AF_LINK][0]['addr']

                            # addresses that already end in .1 represent networks that
                            # a controller can scan for tanks
                            if re.search('\.1$', adr['addr']) is not None:
                                # strip off the 1 and save the network stub
                                self.__networkStubs.append({'IF':i, 'IP':adr['addr'], 'MAC':mac, 'STUB':re.sub('\.1$', '.', adr['addr'])})

                            # addresses that don't end in .1 are interfaces that
                            # a tank can listen on for connections from a controller
                            else:
                                self.__tankAddresses.append({'IF':i, 'IP':adr['addr'], 'MAC':mac})

    def createDisplayWidgets(self, displayType):

        locations = None

        # reuse this method for all the different display fields
        if displayType == 'type': locations = self.__typeLocs
        elif displayType == 'name': locations = self.__nameLocs
        elif displayType == 'interface': locations = self.__interfaceLocs
        elif displayType == 'ip': locations = self.__ipLocs
        elif displayType == 'mac': locations = self.__macLocs
        elif displayType == 'status': locations = self.__statusLocs

        if locations is not None:
            for loc in locations:

                # create the display widget's base frame as a child of its parent
                f = ttk.Frame(loc['parent'], padding='0 0', relief='flat', borderwidth=0)
                f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nw')

                # add a Label widget to show the current value
                l = ttk.Label(f, text='--', font='Arial 16', foreground='#1C4587')
                l.grid(row=0, column=0, sticky='nw')

                # keep a list of widgets for this display
                if displayType == 'type': self.__typeWidgets.append(l)
                elif displayType == 'name': self.__nameWidgets.append(l)
                elif displayType == 'interface': self.__interfaceWidgets.append(l)
                elif displayType == 'ip': self.__ipWidgets.append(l)
                elif displayType == 'mac': self.__macWidgets.append(l)
                elif displayType == 'status': self.__statusWidgets.append(l)

        # children widgets are a little different
        if displayType == 'children' and len(self.__childrenLocs) > 0:

            for loc in self.__childrenLocs:

                # create an empty Frame widget
                f = ttk.Frame(loc['parent'], padding='2', relief='solid', borderwidth=1)
                f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nw')

                # keep a list of children widgets
                self.__childrenWidgets.append(f)

    def updateDisplayWidgets(self, scheduleNext=True):

        # current time
        currentTime = dt.now(tz=tz.utc)

        # default formatting
        fnt = 'Arial 14'
        fgd = '#1C4587'

        # loop through all placements of the type widgets
        for w in self.__typeWidgets:

            # set the update value
            if self.__deviceType is None: upd = '--'
            else: upd = self.__deviceType

            # update the display
            w.config(text=upd, font=fnt, foreground=fgd)
 
        # loop through all placements of the name widgets
        for w in self.__nameWidgets:

            # set the update value
            if self.__id is None: upd = '--'
            else: upd = self.__id

            # update the display
            w.config(text=upd, font=fnt, foreground=fgd)
 
        # loop through all placements of the interface widgets
        for w in self.__interfaceWidgets:

            # set the update value
            if self.__interface is None: upd = '--'
            else: upd = self.__interface

            # update the display
            w.config(text=upd, font=fnt, foreground=fgd)
 
        # loop through all placements of the ip widgets
        for w in self.__ipWidgets:

            # set the update value
            if self.__ip is None: upd = '--'
            else: upd = self.__ip

            # update the display
            w.config(text=upd, font=fnt, foreground=fgd)
 
        # loop through all placements of the mac widgets
        for w in self.__macWidgets:

            # set the update value
            if self.__mac is None: upd = '--'
            else: upd = self.__mac

            # update the display
            w.config(text=upd, font=fnt, foreground=fgd)

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
            w.config(text=upd, font=fnt, foreground=fgd)

        # are there any new children to process?
        if not self.__childrenQueue.empty():

            # grab any newly-reported children and add them to our list
            while not self.__childrenQueue.empty():
                ch = self.__childrenQueue.get_nowait()
                print (f"{self.__class__.__name__}: updateDisplayWidgets: retrieved [{ch}] from childrenQ")

                chvals = ch.split('\n') # type, id, mac, host

                # children dict is keyed off the mac address
                self.__childrenDict[chvals[2]] = {'type':chvals[0], 'id':chvals[1], 'ip':chvals[3]}

                # remember that we've found new children
                self.__newChildren = True

            # complicated sort to properly order e.g. 'Tank 2' before 'Tank 13'
            sortedMacs = sorted(self.__childrenDict, key=lambda x: re.sub(r'0*([0-9]{9,})', r'\1', re.sub(r'([0-9]+)',r'0000000000\1',self.__childrenDict[x]['id'])))

            # loop through all placements of the children widgets
            for w in self.__childrenWidgets:

                # add Label widgets as table headers (each within its own bordered frame)

                f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                f.grid(row=0, column=0, padx='1', pady='1', sticky='nesw')
                ttk.Label(f, text='Name', font='Arial 14 bold').grid(row=0, column=0, sticky='nw')

                f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                f.grid(row=0, column=1, padx='1', pady='1', sticky='nesw')
                ttk.Label(f, text='IP', font='Arial 14 bold').grid(row=0, column=0, sticky='nw')

                f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                f.grid(row=0, column=2, padx='1', pady='1', sticky='nesw')
                ttk.Label(f, text='MAC', font='Arial 14 bold').grid(row=0, column=0, sticky='nw')

                f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                f.grid(row=0, column=3, padx='1', pady='1', sticky='nesw')
                ttk.Label(f, text='Type', font='Arial 14 bold').grid(row=0, column=0, sticky='nw')

                thisrow = 0
                for mac in sortedMacs:
                    thisrow += 1

                    # add Label widgets as table headers (each within its own bordered frame)
                    f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                    f.grid(row=thisrow, column=0, padx='1', pady='1', sticky='nesw')
                    ttk.Label(f, text=self.__childrenDict[mac]['id'],font='Arial 14').grid(row=0, column=0, sticky='nw')

                    f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                    f.grid(row=thisrow, column=1, padx='1', pady='1', sticky='nesw')
                    ttk.Label(f, text=self.__childrenDict[mac]['ip'],font='Arial 14').grid(row=0, column=0, sticky='nw')

                    f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                    f.grid(row=thisrow, column=2, padx='1', pady='1', sticky='nesw')
                    ttk.Label(f, text=mac, font='Arial 14').grid(row=0, column=0, sticky='nw')

                    f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                    f.grid(row=thisrow, column=3, padx='1', pady='1', sticky='nesw')
                    ttk.Label(f, text=self.__childrenDict[mac]['type'],font='Arial 14').grid(row=0, column=0, sticky='nw')

                    print (f"{self.__class__.__name__}: Debug: updateDisplayWidgets: [{thisrow}][{self.__childrenDict[mac]['id']}][{self.__childrenDict[mac]['ip']}][{mac}][{self.__childrenDict[mac]['type']}]")
                print ("")


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
    ttk.Label(root,text='Name:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nse')
    ttk.Label(root,text='Network interface:',font='Arial 14 bold',justify='right').grid(row=3,column=0,sticky='nse')
    ttk.Label(root,text='IP address:',font='Arial 14 bold',justify='right').grid(row=4,column=0,sticky='nse')
    ttk.Label(root,text='MAC address:',font='Arial 14 bold',justify='right').grid(row=5,column=0,sticky='nse')
    ttk.Label(root,text='Last network comms:',font='Arial 14 bold',justify='right').grid(row=6,column=0,sticky='nse')

    childrenFrame = ttk.Frame(root)
    childrenFrame.grid(row=7,column=0,columnspan=2)

    network = Erl2Network(typeLocs=[{'parent':root,'row':1,'column':1}],
                          nameLocs=[{'parent':root,'row':2,'column':1}],
                          interfaceLocs=[{'parent':root,'row':3,'column':1}],
                          ipLocs=[{'parent':root,'row':4,'column':1}],
                          macLocs=[{'parent':root,'row':5,'column':1}],
                          statusLocs=[{'parent':root,'row':6,'column':1}],
                          childrenLocs=[{'parent':childrenFrame,'row':0,'column':0}])

    # set things up for graceful termination
    atexit.register(network.atexitHandler)

    root.mainloop()

if __name__ == "__main__": main()

