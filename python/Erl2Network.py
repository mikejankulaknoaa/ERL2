import atexit
from datetime import datetime as dt
from datetime import timezone as tz
from multiprocessing import Process, Queue
import netifaces
import pickle
import re
import selectors
import socket
from time import sleep
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log

# Erl2Network needs some functions defined outside of the class, because
# in macOS and Windows, you cannot start a process in a subthread if it is
# calling a method of a class with complex attributes (like from tkinter)

# The start of the Erl2Network class definition can be found further down

# port to communicate on
PORT = 65432

# datetime format used to share dates
DTFMT = '%Y-%m-%d %H:%M:%S.%f %Z'

# counter for tracking requests + replies
RQID = 0

def subthreadSendCommand(host,
                         command,
                         commandResultsQ=None,
                         ):

    expected = replyString = replyObj = None

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        try:
            s.settimeout(.5)
            ret = s.connect_ex((host, PORT))

            # something is answering!
            if ret == 0:

                print (f"Erl2Network|subthreadSendCommand: Debug: successfully connected to [{host}][{PORT}]")

                # once socket is successfully connected, lengthen timeout to 10s
                s.settimeout(10)

                # send whatever command we've been told to send
                s.sendall(command)

                # loop for multiple parts of potentially long reply
                while True:

                    # wait for the next 1024 characters
                    data = s.recv(1024)

                    # pick out expected reply length if we don't know it yet
                    if expected is None:

                        # first part of reply is going to be length|payload (variable type = bytes)
                        mat = re.search(b'^([0-9]+)\|(.*)$', data, flags=re.DOTALL)
                        if not mat:
                            raise RuntimeError('Erl2Network|subthreadSendCommand: error: badly formatted reply')

                        # the mat.groups() list is composed of <expected reply length>, <first part of reply>
                        expected = int(mat.groups()[0])
                        replyString = mat.groups()[1]
                        print (f"Erl2Network|subthreadSendCommand: Debug: expecting [{expected}], got [{len(replyString)}]")

                    # add any new bytes to the end of the rest of the reply
                    else:
                        replyString += data
                        print (f"Erl2Network|subthreadSendCommand: Debug: expected [{expected}], TOPPING UP TO [{len(replyString)}]")

                    # check if we've received everything we expected to
                    if len(replyString) >= expected:
                        print (f"Erl2Network|subthreadSendCommand: Debug: expected [{expected}], finished with [{len(replyString)}]")
                        replyObj = SimpleNamespace(addr=host, command=command, replyTime=dt.now(tz=tz.utc), replyString=replyString)
                        break

            else:
                pass
                #print (f"Erl2Network|subthreadSendCommand: Debug: cannot connect to [{host}][{PORT}]: ret [{ret}]")

        except Exception as e:
            print (f"Erl2Network|subthreadSendCommand: Error: unexpected error when connecting to [{host}][{PORT}]: [{e}]")

        finally:
            s.close()

            # communicate reply by queue or by return value
            if commandResultsQ is not None:
                commandResultsQ.put(replyObj)
            else:
                return replyObj

def subthreadScan(stub,
                  interface,
                  ip,
                  mac,
                  ipRange,
                  hardcoding,
                  scanResultsQ,
                  ):

    # quietly terminate if necessary arguments are empty
    if (stub is None or ipRange is None or len(ipRange) != 2) and hardcoding is None:
        return

    # if we're hardcoding a list of child IP addresses, use it
    addressesToScan = hardcoding

    # otherwise, build the list from stub and range
    if addressesToScan is None:
        addressesToScan = []
    for addr in range(ipRange[0], ipRange[1]+1):
            addressesToScan.append(stub + str(addr))

    # scan the specified range of addressed on the subnet
    for host in addressesToScan:

        # ask connected device for identifying details
        idReplyObj = subthreadSendCommand(host, b"GETID")

        # was there a reply?
        if idReplyObj is not None:

            # process device's reply and prepare report for scanResultsQ
            print (f"Erl2Network|subthreadScan: Debug: sent [ID], received reply: [{idReplyObj}]")
            val = '\n'.join([idReplyObj.replyString.decode(), host])

            # grab the replyTime for an initial lastActive value
            val = '\n'.join([val,idReplyObj.replyTime.astimezone(tz.utc).strftime(DTFMT)])

            # add device report to the queue (deviceType, id, mac, ip, lastActive)
            scanResultsQ.put(val)
            #print (f"Erl2Network|subthreadScan: Debug: adding [{val}] to scanResultsQ")

        else:
            pass
            #print (f"Erl2Network|subthreadScan: Debug: cannot connect to [{host}][{PORT}] from [{interface}][{ip}][{mac}]")

def subthreadListen(
                    deviceAddress,
                    incomingQ,
                    outgoingQ,
                    ):

    # initialize selector
    sel = selectors.DefaultSelector()

    # open socket and bind it for listening (non-blocking)
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((deviceAddress, PORT))
    lsock.listen()
    lsock.setblocking(False)
    print (f"Erl2Network|subthreadListen: Debug: listening on {(deviceAddress, PORT)}")

    # register the socket with the selector for listening only (and data set to None)
    sel.register(lsock, selectors.EVENT_READ, data=None)

    try:
        while True:
            # this is a blocking call and should only return when something is received;
            # returns a list of (key, events) tuples where key is a SelectorKey instance
            events = sel.select(timeout=None)

            # loop through list of ready file objects for this selector
            for key, mask in events:

                # no data -- this is the main (READ only) listener socket, receiving a new connection
                if key.data is None:

                    # code formerly part of acceptWrapper
                    sock = key.fileobj

                    conn, addr = sock.accept()  # Should be ready to read
                    print (f"Erl2Network|subthreadListen: Debug: accepted connection from {addr}")
                    conn.setblocking(False)

                    # once a connection is made from a controller, register it for READ and WRITE events
                    events = selectors.EVENT_READ | selectors.EVENT_WRITE
                    data = SimpleNamespace(addr=addr, inb=b"", outb=b"", status=b"CONNECTED")
                    sel.register(conn, events, data=data)

                # data object is present -- so this is a READ / WRITE open connection with a controller
                else:
                    # code formerly part of serviceConnection
                    sock = key.fileobj
                    data = key.data

                    # if this socket was registered with a bitmask including READ events
                    if mask & selectors.EVENT_READ:

                        # receive data from the socket (assumption: requests will never exceed 1024 bytes)
                        recv_data = sock.recv(1024)  # Should be ready to read

                        # something was received
                        if recv_data:

                            print (f"Erl2Network|subthreadListen: Debug: received data {recv_data}")
                            data.inb = recv_data

                            # create a request object, add it to the incoming queue
                            rq = SimpleNamespace(addr=addr, inb=recv_data, outb=b"")
                            incomingQ.put(rq)

                            # update the selectorKey with incoming bytes and status
                            data.outb = b""
                            data.status = b"QUEUED"

                        else:
                            print (f"Erl2Network|subthreadListen: Debug: closing connection to {data.addr}")
                            sel.unregister(sock)
                            sock.close()

                    # if this socket was registered with a bitmask including READ events
                    if mask & selectors.EVENT_WRITE:

                        # check if we're waiting for a reply
                        if data.status == b"QUEUED":

                            # wait up to 10s for a reply
                            countdown=10.
                            while countdown>0.:
                                 if not outgoingQ.empty():
                                     # format answer with length of reply
                                     rq = outgoingQ.get_nowait()
                                     data.outb = str(len(rq.outb)).encode() + b"|" + rq.outb
                                     print (f"Erl2Network|subthreadListen: Debug: read {data.outb} from outgoingQ")
                                     data.status = b"RECEIVED"
                                     break
                                 else:
                                     countdown -= 0.5
                                     sleep(0.5)

                        # if we have a reply
                        if data.outb:

                            print (f"Erl2Network|subthreadListen: Debug: replying {data.outb!r} to {data.addr}")
                            sent = sock.send(data.outb)  # Should be ready to write
                            data.outb = data.outb[sent:]

    except KeyboardInterrupt:
        print (f"Erl2Network|subthreadListen: Debug: caught keyboard interrupt, exiting")

    finally:
        sel.close()

#-----

class Erl2Network():

    # port to communicate on
    PORT = 65432

    def __init__(self,
                 typeLocs=[],
                 idLocs=[],
                 interfaceLocs=[],
                 ipLocs=[],
                 macLocs=[],
                 statusLocs=[],
                 childrenLocs=[],
                 buttonLoc={},
                 systemLog=None,
                 erl2context={}):

        self.__typeLocs = typeLocs
        self.__idLocs = idLocs
        self.__interfaceLocs = interfaceLocs
        self.__ipLocs = ipLocs
        self.__macLocs = macLocs
        self.__statusLocs = statusLocs
        self.__childrenLocs = childrenLocs
        self.__buttonLoc = buttonLoc
        self.__systemLog = systemLog
        self.erl2context = erl2context

        # remember what widgets are active for this network
        self.__typeWidgets = []
        self.__idWidgets = []
        self.__interfaceWidgets = []
        self.__ipWidgets = []
        self.__macWidgets = []
        self.__statusWidgets = []
        self.__childrenWidgets = []
        self.__childrenHeaders = False
        self.__allWidgets = []

        # multithreading: what processes are running, queues for sharing data, received data
        self.__listenProcess = None
        self.__scanProcess = None
        self.__childProcesses = {}
        self.__scanResultsQueue = Queue()
        self.__commandResultsQueue = Queue()
        self.__incomingQueue = Queue()
        self.__outgoingQueue = Queue()

        # last network activity of any kind for this device (less useful for a controller)
        self.__lastActive = None

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # read these useful parameters from Erl2Config
        self.__deviceType = self.erl2context['conf']['device']['type']
        self.__id = self.erl2context['conf']['device']['id']
        self.__controllerIP = self.erl2context['conf']['network']['controllerIP']
        self.__ipNetworkStub = self.erl2context['conf']['network']['ipNetworkStub']
        self.__ipRange = self.erl2context['conf']['network']['ipRange']
        self.__updateFrequency = self.erl2context['conf']['network']['updateFrequency']
        self.__hardcoding = self.erl2context['conf']['network']['hardcoding']

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # this is the main compendium of information about child devices, and their sort order
        self.childrenDict = {}
        self.lookupByIP = {}
        self.lookupByID = {}
        self.sortedMacs = []

        # if the user has overridden the ipRange with None, scan all addresses
        if self.__ipRange is None:
            self.__ipRange = [1, 255]

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load this image that may be needed for Erl2Network controls
        self.erl2context['img'].addImage('rescan', 'network-25.png')

        # details of the network connection(s)
        self.__deviceAddresses = []
        self.__networkStubs = []

        # details of this device's active network connection
        self.__interface = None
        self.__ip = None
        self.__mac = None
        self.__stub = None

        # start by creating the display widgets, if needed
        self.createDisplays('type')
        self.createDisplays('id')
        self.createDisplays('interface')
        self.createDisplays('ip')
        self.createDisplays('mac')
        self.createDisplays('status')
        self.createDisplays('children')

        # determine what IP address(es) are associated with this system's network interfaces
        self.getAddresses()
        print (f"{self.__class__.__name__}: Debug: __init: self.__deviceAddresses is {self.__deviceAddresses}")
        print (f"{self.__class__.__name__}: Debug: __init: self.__networkStubs is {self.__networkStubs}")
        print (f"{self.__class__.__name__}: Debug: __init: self.__hardcoding is {self.__hardcoding}")

        # provide a 'rescan' button (controller only) if given a place for it
        if self.__deviceType == 'controller' and 'parent' in self.__buttonLoc:

            # create a frame for the button
            if 'columnspan' in self.__buttonLoc: cspan = self.__buttonLoc['columnspan']
            else: cspan = 1
            rescanFrame = ttk.Frame(self.__buttonLoc['parent']) #, padding='0', relief='solid', borderwidth=1)
            rescanFrame.grid(row=self.__buttonLoc['row'], column=self.__buttonLoc['column'], columnspan=cspan, sticky='nwse')

            # frame within the frame? for placement (pad with side frames to force it to center)
            f0 = ttk.Frame(rescanFrame) #, padding='0', relief='solid', borderwidth=1)
            f0.grid(row=0, column=0, sticky='nwse')
            f1 = ttk.Frame(rescanFrame) #, padding='0', relief='solid', borderwidth=1)
            f1.grid(row=0, column=1, sticky='nwse')
            f2 = ttk.Frame(rescanFrame) #, padding='0', relief='solid', borderwidth=1)
            f2.grid(row=0, column=2, sticky='nwse')
            rescanFrame.rowconfigure(0,weight=1)
            rescanFrame.columnconfigure(0,weight=1)
            rescanFrame.columnconfigure(1,weight=0)
            rescanFrame.columnconfigure(2,weight=1)

            # create the button, and its clickable label
            rescanButton = tk.Button(f1,
                                     image=self.erl2context['img']['rescan'],
                                     height=40,
                                     width=40,
                                     bd=0,
                                     highlightthickness=0,
                                     activebackground='#DBDBDB',
                                     command=self.rescanSubnet,
                                     )
            rescanButton.grid(row=0, column=0, padx='2 2', sticky='w')
            l = ttk.Label(f1, text='Rescan ERL2 Subnet', font='Arial 16'
                #, relief='solid', borderwidth=1
                )
            l.grid(row=0, column=1, padx='2 2', sticky='w')
            l.bind('<Button-1>', self.rescanSubnet)

            f1.rowconfigure(0,weight=1)
            f1.columnconfigure(0,weight=0)
            f1.columnconfigure(1,weight=1)

        # if controller, start scanning for child devices (only if networkStubs were found)
        if self.__deviceType == 'controller' and len(self.__networkStubs) > 0:

            # populate the display fields with controller-type details
            self.__interface = self.__networkStubs[0]['IF']
            self.__ip = self.__networkStubs[0]['IP']
            self.__mac = self.__networkStubs[0]['MAC']
            self.__stub = self.__networkStubs[0]['STUB']

            # ...however, try to match ipNetworkStub if multiple subnet candidates were found
            if len(self.__deviceAddresses) > 1:
                for ind in range(0, len(self.__deviceAddresses)):
                    if self.__ipNetworkStub in self.__deviceAddresses[ind]:
                        self.__interface = self.__networkStubs[ind]['IF']
                        self.__ip = self.__networkStubs[ind]['IP']
                        self.__mac = self.__networkStubs[ind]['MAC']
                        self.__stub = self.__networkStubs[ind]['STUB']
                        break

            self.updateDisplays()

            # start up the process keep the child device details up to date
            self.pollChildren()

            # run a subnet scan during initialization
            self.rescanSubnet(init=True)

        # if tank, listen for connections from controller (only if deviceAddresses were found)
        elif self.__deviceType == 'tank' and len(self.__deviceAddresses) > 0:

            # default to using the first interface found...
            self.__interface = self.__deviceAddresses[0]['IF']
            self.__ip = self.__deviceAddresses[0]['IP']
            self.__mac = self.__deviceAddresses[0]['MAC']

            # ...however, try to match ipNetworkStub if multiple child device addresses were found
            if len(self.__deviceAddresses) > 1:
                for ind in range(0, len(self.__deviceAddresses)):
                    if self.__ipNetworkStub in self.__deviceAddresses[ind]:
                        self.__interface = self.__deviceAddresses[0]['IF']
                        self.__ip = self.__deviceAddresses[0]['IP']
                        self.__mac = self.__deviceAddresses[0]['MAC']
                        break

            # update the display fields with info about the chosen network interface
            self.updateDisplays()

            self.wrapperListen()

        # start up the process that will answer requests (tanks) and handle those replies (controller)
        self.manageQueues()

    def getAddresses(self):

        # reset lists
        self.__deviceAddresses = []
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

                            # addresses that already end in .1 represent networks that a controller can scan for child devices
                            # (also, the user can override this .1 logic and hardcode the controller IP address)
                            if re.search('\.1$', adr['addr']) is not None or (self.__controllerIP is not None and adr['addr'] == self.__controllerIP):
                                # strip off the last octet and remember the network 'stub'
                                self.__networkStubs.append({'IF':i, 'IP':adr['addr'], 'MAC':mac, 'STUB':re.sub('\.[0-9]+$', '.', adr['addr'])})

                            # addresses that don't end in .1 are interfaces that
                            # a child device can listen on for connections from a controller
                            else:
                                self.__deviceAddresses.append({'IF':i, 'IP':adr['addr'], 'MAC':mac})

    def createDisplays(self, displayType):

        locations = None

        # reuse this method for all the different display fields
        if displayType == 'type': locations = self.__typeLocs
        elif displayType == 'id': locations = self.__idLocs
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
                l = ttk.Label(f, text='--', font='Arial 14')
                l.grid(row=0, column=0, sticky='nw')

                # keep a list of widgets for this display
                if displayType == 'type': self.__typeWidgets.append(l)
                elif displayType == 'id': self.__idWidgets.append(l)
                elif displayType == 'interface': self.__interfaceWidgets.append(l)
                elif displayType == 'ip': self.__ipWidgets.append(l)
                elif displayType == 'mac': self.__macWidgets.append(l)
                elif displayType == 'status': self.__statusWidgets.append(l)

                # keep a separate list of all widgets
                self.__allWidgets.append(l)

        # children widgets are a little different
        if displayType == 'children' and len(self.__childrenLocs) > 0:

            for loc in self.__childrenLocs:

                # create an empty Frame widget
                if 'columnspan' in loc: cspan = loc['columnspan']
                else: cspan = 1
                f = ttk.Frame(loc['parent'], padding='2', relief='solid', borderwidth=1)
                f.grid(row=loc['row'], column=loc['column'], columnspan=cspan, padx='2', pady='0', sticky='nw')

                # keep a list of children widgets
                self.__childrenWidgets.append(f)

                # keep a separate list of all widgets
                self.__allWidgets.append(f)

    def updateDisplays(self, scheduleNext=True):

        # current time
        currentTime = dt.now(tz=tz.utc)

        # default font
        fnt = 'Arial 14'

        # loop through all placements of the type widgets
        for w in self.__typeWidgets:

            # set the update value
            if self.__deviceType is None: upd = '--'
            else: upd = self.__deviceType

            # update the display
            w.config(text=upd, font=fnt)
 
        # loop through all placements of the id widgets
        for w in self.__idWidgets:

            # set the update value
            if self.__id is None: upd = '--'
            else: upd = self.__id

            # update the display
            w.config(text=upd, font=fnt)
 
        # loop through all placements of the interface widgets
        for w in self.__interfaceWidgets:

            # set the update value
            if self.__interface is None: upd = '--'
            else: upd = self.__interface

            # update the display
            w.config(text=upd, font=fnt)
 
        # loop through all placements of the ip widgets
        for w in self.__ipWidgets:

            # set the update value
            if self.__ip is None: upd = '--'
            else: upd = self.__ip

            # update the display
            w.config(text=upd, font=fnt)
 
        # loop through all placements of the mac widgets
        for w in self.__macWidgets:

            # set the update value
            if self.__mac is None: upd = '--'
            else: upd = self.__mac

            # update the display
            w.config(text=upd, font=fnt)

        # set the update value
        if self.__lastActive is None: upd = 'never'
        else: upd = self.__lastActive.astimezone(self.__timezone).strftime(self.__dtFormat)

        # adjust the formatting if the communications have gone quiet
        if self.__lastActive is None or currentTime.timestamp() - self.__lastActive.timestamp() > 300:
            fnt = 'Arial 14 bold'
            fgd = '#A93226' # red
        else:
            fnt = 'Arial 14'
            fgd = '#1C4587' # blue

        # loop through all placements of the status widgets
        for w in self.__statusWidgets:

            # update the display
            w.config(text=upd, font=fnt, foreground=fgd)

        # are there any new scan results to process?
        if not self.__scanResultsQueue.empty():

            # grab any newly-reported children and add them to our list
            while not self.__scanResultsQueue.empty():
                ch = self.__scanResultsQueue.get_nowait()
                #print (f"{self.__class__.__name__}: updateDisplays: retrieved [{ch}] from scanResultsQ")

                # device report from the queue has the following fields
                keyNames = ['deviceType', 'id', 'mac', 'ip', 'lastActive']

                # device report is delimited by LF
                chvals = ch.split('\n')

                # new dict value
                newDict = {}

                # assign dict values
                for key, val in zip(keyNames, chvals):
                    newDict[key] = val
                    #print (f"{self.__class__.__name__}: updateDisplays: assigning [{val}] to [{key}]")

                # store lastActive as a datetime
                newDict['lastActive'] = dt.strptime(newDict['lastActive'], DTFMT)

                # strptime seems to drop timezone info, so add it back explicitly
                newDict['lastActive'] = newDict['lastActive'].replace(tzinfo=tz.utc)

                # children dict is keyed off the mac address
                self.childrenDict[newDict['mac']] = newDict

            # complicated sort to properly order e.g. 'Tank 2' before 'Tank 13'
            self.sortedMacs = sorted(self.childrenDict, key=lambda x: re.sub(r'0*([0-9]{9,})', r'\1', re.sub(r'([0-9]+)',r'0000000000\1',self.childrenDict[x]['id'])))

            # redo lookups from scratch
            oldLookupByID = self.lookupByID
            oldLookupByIP = self.lookupByIP
            self.lookupByID = {}
            self.lookupByIP = {}
            for mac in self.sortedMacs:
                id = self.childrenDict[mac]['id']
                ip = self.childrenDict[mac]['ip']

                # duplicate child id??
                if id in self.lookupByID:
                    self.childrenDict[mac]['ignore'] = True
                    mb.showerror(f"Error: more than one active child device has " +
                                 f"the ID [{id}]; ignoring the one at [{mac}][{ip}]. " +
                                 f"Please shut down one of the conflicting devices " +
                                 f"and give it a new ID in its erl2.conf configuration file.")

                else:
                    self.childrenDict[mac]['ignore'] = False

                    # new device (mac address) for a Tank ID we've seen before?
                    if (id in oldLookupByID and oldLookupByID[id] != mac):
                        mb.showwarning(f"Warning: Tank ID [{id}] is online with a different " +
                                       f"mac address; before [{oldLookupByID[id]}], after [{mac}].")

                    # new ip address for a Tank ID we've seen before?
                    if (ip in oldLookupByIP and oldLookupByIP[ip] != mac):
                        oldIP = [x for x in oldLookupByIP if oldLookupByIP==ip][0]
                        mb.showwarning(f"Warning: Tank ID [{id}] is online with a different " +
                                       f"ip address; before [{oldIP}], after [{ip}].")

                    # add these entries to the new lookup dicts
                    self.lookupByID[id] = mac
                    self.lookupByIP[ip] = mac

        # only draw the childrenWidgets headers once
        if not self.__childrenHeaders:
            self.__childrenHeaders = True

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
                ttk.Label(f, text='Last Active', font='Arial 14 bold').grid(row=0, column=0, sticky='nw')

                f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                f.grid(row=0, column=4, padx='1', pady='1', sticky='nesw')
                ttk.Label(f, text='Latency', font='Arial 14 bold').grid(row=0, column=0, sticky='nw')

        # only makes sense if any children were found
        if len(self.childrenDict) > 0:

            # loop through all placements of the children widgets
            for w in self.__childrenWidgets:

                thisrow = 0
                for mac in self.sortedMacs:

                    thisrow += 1

                    # special formatting for lastActive
                    lastA = self.childrenDict[mac]['lastActive']
                    upd = lastA.astimezone(self.__timezone).strftime(self.__dtFormat)
                    if lastA is None or currentTime.timestamp() - lastA.timestamp() > 300:
                        fnt = 'Arial 14 bold'
                        fgd = '#A93226' # red
                    else:
                        fnt = 'Arial 14'
                        fgd = '#1C4587' # blue

                    # latency might not be populated at first
                    if 'latency' not in self.childrenDict[mac]: lat = '--'
                    else: lat = round(self.childrenDict[mac]['latency'],5)

                    # if this is a new row in the grid (pls forgive the offensive tkinter method name)...
                    if (len(w.grid_slaves(row=thisrow,column=4))==0):

                        #print (f"{self.__class__.__name__}: Debug: updateDisplays: THIS IS A NEW ROW")

                        f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                        f.grid(row=thisrow, column=0, padx='1', pady='1', sticky='nesw')
                        ttk.Label(f, text=self.childrenDict[mac]['id'],font='Arial 14').grid(row=0, column=0, sticky='nw')

                        f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                        f.grid(row=thisrow, column=1, padx='1', pady='1', sticky='nesw')
                        ttk.Label(f, text=self.childrenDict[mac]['ip'],font='Arial 14').grid(row=0, column=0, sticky='nw')

                        f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                        f.grid(row=thisrow, column=2, padx='1', pady='1', sticky='nesw')
                        ttk.Label(f, text=mac, font='Arial 14').grid(row=0, column=0, sticky='nw')

                        f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                        f.grid(row=thisrow, column=3, padx='1', pady='1', sticky='nesw')
                        ttk.Label(f, text=upd, font=fnt, foreground=fgd).grid(row=0, column=0, sticky='nw')

                        f = ttk.Frame(w, padding='2', relief='solid', borderwidth=1)
                        f.grid(row=thisrow, column=4, padx='1', pady='1', sticky='nesw')
                        ttk.Label(f, text=lat,font='Arial 14').grid(row=0, column=0, sticky='nw')

                    else:
                        # more references to tkinter's offensive method name
                        #print (f"{self.__class__.__name__}: Debug: updateDisplays: FOUND AN EXISTING ROW [{w.grid_slaves(row=thisrow,column=4)}]")
                        w.grid_slaves(row=thisrow,column=0)[0].grid_slaves(row=0,column=0)[0].config(text=self.childrenDict[mac]['id'])
                        w.grid_slaves(row=thisrow,column=1)[0].grid_slaves(row=0,column=0)[0].config(text=self.childrenDict[mac]['ip'])
                        w.grid_slaves(row=thisrow,column=2)[0].grid_slaves(row=0,column=0)[0].config(text=mac)
                        w.grid_slaves(row=thisrow,column=3)[0].grid_slaves(row=0,column=0)[0].config(text=upd, font=fnt, foreground=fgd)
                        w.grid_slaves(row=thisrow,column=4)[0].grid_slaves(row=0,column=0)[0].config(text=lat)

        # if asked to, schedule the next display update
        if scheduleNext:

            # update on schedule
            nextUpdateTime = Erl2Log.nextIntervalTime(currentTime, self.__updateFrequency)
            delay = int((nextUpdateTime - currentTime.timestamp())*1000)
        
            # update the display widgets again after waiting an appropriate number of milliseconds
            self.__allWidgets[0].after(delay, self.updateDisplays)

    def rescanSubnet(self, event=None, init=False):

        if self.scanning():
            mb.showinfo(title='Rescan ERL2 Subnet', message="Another scan is already running.")

        else:
            # ask for confirmation unless this is the first scan during initialization
            if init or (mb.askyesno(title='Rescan ERL2 Subnet', message="Are you sure you want to scan for new devices on the ERL2 subnet?")):
                self.wrapperScan()

    def wrapperListen(self):

        # do this in a separate process thread
        self.__listenProcess = Process(target=subthreadListen,
                                       args=(self.__deviceAddresses[0]['IP'],
                                             self.__incomingQueue,
                                             self.__outgoingQueue,
                                             ))
        self.__listenProcess.start()

    def wrapperScan(self):

        # do this in a separate process thread
        self.__scanProcess = Process(target=subthreadScan,
                                     args=(self.__stub,
                                           self.__interface,
                                           self.__ip,
                                           self.__mac,
                                           self.__ipRange,
                                           self.__hardcoding,
                                           self.__scanResultsQueue,
                                           ))
        self.__scanProcess.start()

    def wrapperSendCommand(self, mac, command, commandResultsQ):

        # do this in a separate process thread
        proc = Process(target=subthreadSendCommand,
                       args=(self.childrenDict[mac]['ip'],
                             command,
                             commandResultsQ,
                             ))

        # clean up the list of child processes, or create it if it doesn't exist yet
        if mac in self.__childProcesses:
            p = 0
            while p < len(self.__childProcesses[mac]):
                if self.__childProcesses[mac][p].is_alive():
                    p += 1
                else:
                    del self.__childProcesses[mac][p]
        else:
            self.__childProcesses[mac] = []

        # add the new process and start() it
        self.__childProcesses[mac].append(proc)
        proc.start()

    def manageQueues(self):

        # are there any new requests to process?
        if not self.__incomingQueue.empty():

            # loop through all pending requests
            while not self.__incomingQueue.empty():
                rq = self.__incomingQueue.get_nowait()
                print (f"{self.__class__.__name__}: manageQueues: retrieved [{rq}] from self.__incomingQueue")
                print (f"{self.__class__.__name__}: manageQueues: self.__incomingQueue[{rq.addr}] retrieved [{rq}]")

                # GETID: n/a, this is answered directly within the listen() process
                if rq.inb == b"GETID":
                    rq.outb = '\n'.join([self.__deviceType, self.__id, f"{self.__mac}"]).encode()

                # GETTIME: answer with a datetime instance (pickled)
                elif rq.inb == b"GETTIME":
                    rq.outb = pickle.dumps(dt.now(tz=tz.utc))

                # GETSTATE: answer with an Erl2State instance (pickled)
                elif rq.inb == b"GETSTATE":
                    rq.outb = pickle.dumps(self.erl2context['state'])

                # GETLOG: answer with an export of logs from Erl2Log (pickled)
                elif re.match(b"^GETLOG", rq.inb):

                    # unpack second parameter (most recent timestamp already sent)
                    mat = re.search(b'^GETLOG\|(.*)$', rq.inb)
                    if not mat:
                        raise RuntimeError('Erl2Network|manageQueues: error: badly formatted request')

                    # the mat.groups() list should just be one item, the timestamp parameter
                    ts = mat.groups()[0]
                    if ts == b'None':
                        ts = None
                    else:
                        # convert ts to a datetime
                        ts = dt.strptime(ts.decode(), DTFMT)

                        # strptime seems to drop timezone info, so add it back explicitly
                        ts = ts.replace(tzinfo=tz.utc)

                    print (f"Erl2Network|manageQueues: Debug: request [{rq.inb}] timestamp [{ts}]")
                    rq.outb = pickle.dumps(self.__systemLog.exportLog(ts))

                # unrecognized request: answer with error
                else:
                    rq.outb = 'error: unrecognized request'.encode()

                # add reply to the outgoing queue
                self.__outgoingQueue.put(rq)

                # update time of last device comms
                self.__lastActive = dt.now(tz=tz.utc)

        # are there any command results to process?
        if not self.__commandResultsQueue.empty():

            # loop through all pending results
            while not self.__commandResultsQueue.empty():

                # retrieve the command results and figure out what mac address they're for
                rs = self.__commandResultsQueue.get_nowait()

                # can get_nowait() return something that isn't a request?
                if rs is not None and hasattr(rs, "addr"):
                    mac = self.lookupByIP[rs.addr]

                    print (f"{self.__class__.__name__}: manageQueues: self.__commandResultsQueue[{rs.addr}][{mac}] retrieved [{rs}]")

                    # no matter what type of comms, update the lastActive timestamp
                    self.childrenDict[mac]['lastActive'] = rs.replyTime

                    if rs.command == b"GETID":

                         # we'll want to compare new results against the old
                         # (if changes, trigger another full network scan)
                         pass

                    elif rs.command == b"GETTIME":

                        # unpack reply, which is a pickled datetime instance
                        deviceT = pickle.loads(rs.replyString)

                        # calculate difference in controller/device clocks
                        self.childrenDict[mac]['latency'] = (deviceT-rs.replyTime).total_seconds()
                        print (f"{self.__class__.__name__}: manageQueues: updating latency for [{mac}] to [{self.childrenDict[mac]['latency']}]")

                    elif rs.command == b"GETSTATE":

                         # answered with an Erl2State instance (pickled)
                         self.childrenDict[mac]['state'] = pickle.loads(rs.replyString)

                    elif re.match(b'^GETLOG|', rs.command):

                        # answered with a value from an Erl2Log instance (pickled)
                        # NOT IMPLEMENTED YET
                        print (f"{self.__class__.__name__}: manageQueues: got an answer to request [{rs.command}] but this isn't implemented yet")
                        pass

        # call this method again after waiting 1s
        self.__allWidgets[1].after(1000, self.manageQueues)

    def pollChildren(self):

        # skip processing if we're scanning the network for new devices
        if not self.scanning():

            # loop through child devices
            for mac in self.sortedMacs:

                # check id
                self.sendCommand(mac, b"GETID")

                # update latency (get time)
                self.sendCommand(mac, b"GETTIME")

                # get state
                self.sendCommand(mac, b"GETSTATE")

                # get log (include info about timestamps already received)
                if 'logs' in self.childrenDict[mac] and self.childrenDict[mac].latestTS is not None:
                    lastLog = self.childrenDict[mac]['logs'].latestTS.astimezone(tz.utc).strftime(DTFMT)
                else:
                    lastLog = 'None'
                self.sendCommand(mac, b"GETLOG" + b"|" + lastLog.encode())

        # call this method again after waiting 30s
        self.__allWidgets[2].after(30000, self.pollChildren)

    def scanning(self):
        return self.__scanProcess is not None and self.__scanProcess.is_alive()

    def sendCommand(self, mac, command):

        # send command and give it a queue for its reply
        self.wrapperSendCommand(mac, command, self.__commandResultsQueue)

    # atexit.register() handler
    def atexitHandler(self):

        #print (f"{self.__class__.__name__}: Debug: atexitHandler() called")
    
        # kill off the forked process listening for connections
        if self.__listenProcess is not None and self.__listenProcess.is_alive():
            self.__listenProcess.kill()

        # kill off the forked process scanning for child devices
        if self.__scanProcess is not None and self.__scanProcess.is_alive():
            self.__scanProcess.kill()

        # kill off any child processes
        for mac in self.sortedMacs:
            if mac in self.__childProcesses:
                for p in self.__childProcesses[mac]:
                    if p.is_alive():
                        p.kill()

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
                          childrenLocs=[{'parent':childrenFrame,'row':0,'column':0}],
                          buttonLoc={'parent':root,'row':8,'column':0,'columnspan':2},
                          )

    # set things up for graceful termination
    atexit.register(network.atexitHandler)

    root.mainloop()

if __name__ == "__main__": main()

