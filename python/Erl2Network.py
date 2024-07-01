import atexit
from datetime import datetime as dt
from datetime import timezone as tz
from multiprocessing import Process, Queue
import netifaces
import pickle
import re
import selectors
import socket
from sys import getsizeof
from time import sleep
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as mb
from Erl2Config import Erl2Config
from Erl2Image import Erl2Image
from Erl2Log import Erl2Log
from Erl2State import Erl2State
from Erl2Useful import locDefaults, nextIntervalTime

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

                #print (f"Erl2Network|subthreadSendCommand: Debug: successfully connected to [{host}][{PORT}]")

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
                        #print (f"Erl2Network|subthreadSendCommand: Debug: expecting [{expected}], got [{len(replyString)}]")

                    # add any new bytes to the end of the rest of the reply
                    else:
                        replyString += data
                        #print (f"Erl2Network|subthreadSendCommand: Debug: expected [{expected}], TOPPING UP TO [{len(replyString)}]")

                    # check if we've received everything we expected to
                    if len(replyString) >= expected:
                        #print (f"Erl2Network|subthreadSendCommand: Debug: expected [{expected}], finished with [{len(replyString)}]")
                        replyObj = SimpleNamespace(addr=host, command=command, replyTime=dt.now(tz=tz.utc), replyString=replyString)
                        break

            else:
                pass
                #print (f"Erl2Network|subthreadSendCommand: Debug: cannot connect to [{host}][{PORT}]: ret [{ret}]")

        except Exception as e:
            pass
            #print (f"Erl2Network|subthreadSendCommand: Error: unexpected error when connecting to [{host}][{PORT}]: [{e}]")

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

            # there could be decoding problems
            try:
                # process device's reply and prepare report for scanResultsQ
                #print (f"Erl2Network|subthreadScan: Debug: sent [ID], received reply: [{idReplyObj}]")
                val = '\n'.join([idReplyObj.replyString.decode(), host])

                # grab the replyTime for an initial lastActive value
                val = '\n'.join([val,idReplyObj.replyTime.astimezone(tz.utc).strftime(DTFMT)])

                # add device report to the queue (deviceType, id, mac, ip, lastActive)
                scanResultsQ.put(val)
                #print (f"Erl2Network|subthreadScan: Debug: adding [{val}] to scanResultsQ")

            except UnicodeDecodeError as e:
                print (f"Erl2Network|subthreadScan: Warning: UnicodeDecodeError in reply [{idReplyObj.replyString[:50]}]")

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
    #print (f"Erl2Network|subthreadListen: Debug: listening on {(deviceAddress, PORT)}")

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
                    #print (f"Erl2Network|subthreadListen: Debug: accepted connection from {addr}")
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

                            #print (f"Erl2Network|subthreadListen: Debug: received data {recv_data}")
                            data.inb = recv_data

                            # create a request object, add it to the incoming queue
                            rq = SimpleNamespace(addr=addr, inb=recv_data, outb=b"")
                            incomingQ.put(rq)

                            # update the selectorKey with incoming bytes and status
                            data.outb = b""
                            data.status = b"QUEUED"

                        else:
                            #print (f"Erl2Network|subthreadListen: Debug: closing connection to {data.addr}")
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
                                     #print (f"Erl2Network|subthreadListen: Debug: read {data.outb} from outgoingQ")
                                     data.status = b"RECEIVED"
                                     break
                                 else:
                                     countdown -= 0.5
                                     sleep(0.5)

                        # if we have a reply
                        if data.outb:

                            #print (f"Erl2Network|subthreadListen: Debug: replying {data.outb!r} to {data.addr}")
                            sent = sock.send(data.outb)  # Should be ready to write
                            data.outb = data.outb[sent:]

    except KeyboardInterrupt:
        pass
        #print (f"Erl2Network|subthreadListen: Debug: caught keyboard interrupt, exiting")

    finally:
        sel.close()

#-----

class Erl2Network():

    # port to communicate on
    PORT = 65432

    def __init__(self,
                 standalone=False,
                 typeLocs=[],
                 nameLocs=[],
                 interfaceLocs=[],
                 ipLocs=[],
                 macLocs=[],
                 statusLocs=[],
                 buttonLocs=[],
                 childrenLocs=[],
                 onlineLocs=[],
                 systemLog=None,
                 erl2context={}):

        self.__standalone = standalone
        self.__systemLog = systemLog
        self.erl2context = erl2context

        # insist on 'root' always being defined
        assert('root' in self.erl2context and self.erl2context['root'] is not None)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # load any saved info about the application state
        if 'state' not in self.erl2context:
            self.erl2context['state'] = Erl2State(erl2context=self.erl2context)

        # if necessary, create an object to hold/remember image objects
        if 'img' not in self.erl2context:
            self.erl2context['img'] = Erl2Image(erl2context=self.erl2context)

        # load this image that may be needed for Erl2Network controls
        self.erl2context['img'].addImage('rescan', 'network-25.png')

        # and these images are for the online / offline indicator
        self.erl2context['img'].addImage('online', 'network-on-25.png')
        self.erl2context['img'].addImage('offline', 'network-off-25.png')
        self.__onlineImages=[self.erl2context['img']['offline'],
                             self.erl2context['img']['online']]

        # remember what widgets are active for this network
        self.__childrenHeaders = False
        self.__netWidgets = {}

        # .after() scheduling requires dedicated widgets (and Erl2Network may not use widgets)
        self.__afterUpdateDisplays = None
        self.__afterManageQueues = None
        self.__afterPollChildren = None

        # multithreading: what processes are running, queues for sharing data, received data
        self.__listenProcess = None
        self.__listenTime = None
        self.__scanProcess = None
        self.__childProcesses = {}
        self.__scanResultsQueue = Queue()
        self.__commandResultsQueue = Queue()
        self.__incomingQueue = Queue()
        self.__outgoingQueue = Queue()

        # last network activity of any kind for this device (less useful for a controller)
        self.__lastActive = self.erl2context['state'].get('network','lastActive',None)

        # read these useful parameters from Erl2Config
        self.__deviceType = self.erl2context['conf']['device']['type']
        self.__id = self.erl2context['conf']['device']['id']
        self.__controllerIP = self.erl2context['conf']['network']['controllerIP']
        self.__ipNetworkStub = self.erl2context['conf']['network']['ipNetworkStub']
        self.__ipRange = self.erl2context['conf']['network']['ipRange']
        self.__hardcoding = self.erl2context['conf']['network']['hardcoding']
        self.__updateFrequency = self.erl2context['conf']['network']['updateFrequency']
        self.__lapseTime = self.erl2context['conf']['network']['lapseTime']

        # and also these system-level Erl2Config parameters
        self.__timezone = self.erl2context['conf']['system']['timezone']
        self.__dtFormat = self.erl2context['conf']['system']['dtFormat']

        # keep track of when certain network updates were last done
        self.__lastTIME = None
        self.__lastSTATE = None
        self.__lastLOG = None

        # start a data/log file for the network
        self.__networkLog = Erl2Log(logType='system', logName='Erl2Network', erl2context=self.erl2context)

        # this is the main compendium of information about child devices, and their sort order
        self.childrenDict = self.erl2context['state'].get('network','childrenDict',{})

        # system's memory of what unique IDs have been used locally for filenames
        self.allInternalIDs = self.erl2context['state'].get('network','allInternalIDs',[])

        #print (f"{self.__class__.__name__}: __init: Debug: self.childrenDict type:[{type(self.childrenDict).__name__}] is {self.childrenDict}")
        #print (f"{self.__class__.__name__}: __init: Debug: self.allInternalIDs type:[{type(self.allInternalIDs).__name__}] is {self.allInternalIDs}")

        # helpful data structures used to reference entries in childrenDict
        self.sortedMacs = self.createSortedMacs()
        self.lookupByID, self.lookupByIP = self.createLookups()

        # Erl2States, Erl2Readouts and Erl2Logs associated with child devices
        self.childrenStates = {}
        self.childrenReadouts = {}
        self.childrenLogs = {}

        # loop through all child devices to load data already saved on controller
        for thisMac in self.sortedMacs:

            # need to have the internalID defined for this to work
            if 'internalID' in self.childrenDict[thisMac]:

                # load Erl2State info for child devices if any stored locally
                self.childrenStates[thisMac] = Erl2State(internalID=self.childrenDict[thisMac]['internalID'],
                                                         erl2context=self.erl2context)

                # load Erl2Log info for child devices if any stored locally
                self.childrenLogs[thisMac] = Erl2Log(logType='device',
                                                     logName=self.childrenDict[thisMac]['internalID'],
                                                     erl2context=self.erl2context)

        # if the user has overridden the ipRange with None, scan all addresses
        if self.__ipRange is None:
            self.__ipRange = [1, 255]

        # details of the network connection(s)
        self.__deviceAddresses = []
        self.__networkStubs = []

        # details of this device's active network connection
        self.__interface = None
        self.__ip = None
        self.__mac = None
        self.__stub = None

        # determine what IP address(es) are associated with this system's network interfaces
        self.getAddresses()
        #print (f"{self.__class__.__name__}: __init: Debug: self.__deviceAddresses is {self.__deviceAddresses}")
        #print (f"{self.__class__.__name__}: __init: Debug: self.__networkStubs is {self.__networkStubs}")
        #print (f"{self.__class__.__name__}: __init: Debug: self.__hardcoding is {self.__hardcoding}")

        # location defaults for network module
        self.modDefaults={'relief':'flat', 'borderwidth':0, 'padx':'0', 'pady':'0', 'sticky':'nw'}

        # widget creation can be done at instantiation or later with separate addWidgets call
        if (len(typeLocs) + len(nameLocs) + len(interfaceLocs) + len(ipLocs) + len(macLocs)
                + len(statusLocs) + len(buttonLocs) + len(childrenLocs) > 0):

            self.addWidgets(typeLocs=typeLocs,
                            nameLocs=nameLocs,
                            interfaceLocs=interfaceLocs,
                            ipLocs=ipLocs,
                            macLocs=macLocs,
                            statusLocs=statusLocs,
                            buttonLocs=buttonLocs,
                            childrenLocs=childrenLocs,
                            onlineLocs=onlineLocs,
                            )

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

            # controller startup log message
            self.__networkLog.writeMessage(f"Controller startup at interface [{self.__interface}], ip [{self.__ip}], mac [{self.__mac}]")

            # start up the process keep the child device details up to date
            self.pollChildren()

            ## run a subnet scan during initialization
            #self.rescanSubnet(init=True)

        # if tank, listen for connections from controller (only if deviceAddresses were found)
        elif self.__deviceType == 'tank' and len(self.__deviceAddresses) > 0:

            # based on results of getAddresses(), chose an interface to listen on
            self.chooseTankInterface()

            # tank startup log message
            self.__networkLog.writeMessage(f"Tank startup at interface [{self.__interface}], ip [{self.__ip}], mac [{self.__mac}]")

            # start up the process that will listen for controller comms in a subthread
            self.wrapperListen()

        # update the display fields with info about the active network interface
        self.updateDisplays()

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

    def chooseTankInterface(self):

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

    def updateDisplays(self, scheduleNext=True):

        # current time
        currentTime = dt.now(tz=tz.utc)

        #print (f"{self.__class__.__name__}: updateDisplays: Debug: called at [{currentTime}]")

        # check if there are any results queued up from a (completed) subnet scan
        if not self.scanning() and not self.__scanResultsQueue.empty():

            newChildrenDict = {}

            # build a new list of results from this scan
            while not self.__scanResultsQueue.empty():

                ch = self.__scanResultsQueue.get_nowait()
                #print (f"{self.__class__.__name__}: updateDisplays: Debug: retrieved [{ch}] from scanResultsQ")

                # device report from the queue has the following fields
                keyNames = ['deviceType', 'id', 'mac', 'ip', 'lastActive']

                # device report is delimited by LF
                chvals = ch.split('\n')

                # new child device dictionary entry
                newEntry = {}

                # assign individual values to new child device dictionary entry
                for key, val in zip(keyNames, chvals):
                    newEntry[key] = val
                    #print (f"{self.__class__.__name__}: updateDisplays: Debug: assigning [{val}] to [{key}]")

                # except it's not necessary to store mac in the entry when it's used as the key
                newMac = newEntry.pop('mac')

                # store lastActive as a datetime
                newEntry['lastActive'] = dt.strptime(newEntry['lastActive'], DTFMT).replace(tzinfo=tz.utc)

                # add to this list of new scan results indexed by mac
                newChildrenDict[newMac] = newEntry

            # create a sorted list of keys for this dict of scan results
            newSortedMacs = self.createSortedMacs(newChildrenDict)

            # find any duplicate IDs in this set of results
            duplicates = {}
            for thisMac in newSortedMacs:
                thisID = newChildrenDict[thisMac]['id']
                if thisID in duplicates:
                    duplicates[thisID].append(thisMac)
                else:
                    duplicates[thisID] = [thisMac]

            # resolve duplicate IDs
            for thisID in duplicates:
                if len(duplicates[thisID]) > 1:

                    # loop through macs that share this id
                    chosenMac = None
                    for thisMac in duplicates[thisID]:

                        # choose this one if this same mac was already in our list with the same id
                        if thisMac in self.childrenDict and self.childrenDict[thisMac]['id'] == thisId:
                            chosenMac = thisMac
                            break

                    # otherwise, arbitrarily choose the first mac
                    else:
                        chosenMac = duplicates[thisID][0]

                    # remove the chosen mac from the list of duplicates
                    duplicates[thisID].remove[chosenMac]

                    # finessing the warning message language...
                    if len(duplicates[thisID]) > 1:
                        plur = 's'
                        pron = 'their'
                    else:
                        plur = 'its'

                    # list macs and ips for warning message
                    dupMacsAndIPs = []
                    for thisMac in duplicates[thisID]:
                        dupMacsAndIPs.append(f"[{thisMac}][{newChildrenDict[thisMac]['ip']}]")

                    # create an alert about duplicate IDs
                    mb.showerror(f"Error: more than one active child device has the ID [{id}]; " +
                                 f"keeping [{chosenMac}][{newChildrenDict[chosenMac]['ip']}] and " +
                                 f"ignoring the one{plur} at {', '.join(dupMacsAndIPs)}. " +
                                 f"Please shut down the conflicting device{plur} " +
                                 f"and edit the ID in {pron} erl2.conf configuration file{plur}.",
                                 parent=self.erl2context['root'])

                    # note duplicate ids in log
                    self.__networkLog.writeMessage(f"scan results: duplicate IDs, keeping " +
                                                   f"[{chosenMac}][{newChildrenDict[chosenMac]['ip']}] " +
                                                   f"and ignoring {', '.join(dupMacsAndIPs)}")

                    # forget all devices with this ID that weren't "chosen"
                    for thisMac in duplicates[thisID]:
                        if thisMac != chosenMac:
                            newChildrenDict.pop(thisMac)
                            newSortedMacs.remove(thisMac)

            # remember if any changes were made to the children dictionary
            dictChanged = False

            # loop through any new children
            for thisMac in newSortedMacs:

                #print (f"{self.__class__.__name__}: updateDisplays: Debug: [{thisMac}] in scan results")

                # check if this mac is already in the list with the same id
                if (    thisMac in self.childrenDict
                    and self.childrenDict[thisMac]['id'] == newChildrenDict[thisMac]['id']):

                    #print (f"{self.__class__.__name__}: updateDisplays: Debug: [{thisMac}] already in childrenDict")

                    # this is considered to be the "same" device, so check for changes and update it
                    thisID = self.childrenDict[thisMac]['id']

                    # warn if device type has changed, then update it
                    if self.childrenDict[thisMac]['deviceType'] != newChildrenDict[thisMac]['deviceType']:
                        oldType = self.childrenDict[thisMac]['deviceType']
                        newType = newChildrenDict[thisMac]['deviceType']
                        mb.showwarning(f"Warning: Device ID [{thisID}] used to be online with " +
                                       f"device type [{oldType}] but now has device type [{newType}]. " +
                                       f"Previous settings and data will be retained.",
                                       parent=self.erl2context['root'])
                        self.childrenDict[thisMac]['deviceType'] = newChildrenDict[thisMac]['deviceType']
                        dictChanged = True

                        # note the changed device type in log
                        self.__networkLog.writeMessage(f"scan results: ID [{thisID}] changed " +
                                                       f"device type from [{oldType}] to [{newType}]")

                    # warn if ip address has changed, then update it
                    if self.childrenDict[thisMac]['ip'] != newChildrenDict[thisMac]['ip']:
                        oldIP = self.childrenDict[thisMac]['ip']
                        newIP = newChildrenDict[thisMac]['ip']
                        mb.showwarning(f"Warning: Device ID [{thisID}] used to be online with " +
                                       f"IP address [{oldIP}] but now has IP address [{newIP}]. " +
                                       f"Previous settings and data will be retained.",
                                       parent=self.erl2context['root'])
                        self.childrenDict[thisMac]['ip'] = newChildrenDict[thisMac]['ip']
                        dictChanged = True

                        # note the changed ip address in log
                        self.__networkLog.writeMessage(f"scan results: ID [{thisID}] changed " +
                                                       f"IP address from [{oldIP}] to [{newIP}]")

                    # copy new lastActive date into main dict
                    self.childrenDict[thisMac]['lastActive'] = newChildrenDict[thisMac]['lastActive']
                    dictChanged = True

                # otherwise, check if this mac was in the old list but with a different ID
                elif thisMac in self.childrenDict:

                    #print (f"{self.__class__.__name__}: updateDisplays: Debug: [{thisMac}] same MAC, different ID")

                    oldID = self.childrenDict[thisMac]['id']
                    newID = newChildrenDict[thisMac]['id']
                    mb.showwarning(f"Warning: MAC address [{thisMac}] used to be online with " +
                                   f"Device ID [{oldID}] but now has Device ID [{newID}]. " +
                                   f"Previous settings and data will be discarded and everything " +
                                   f"loaded anew from the device.",
                                   parent=self.erl2context['root'])
                    self.childrenDict[thisMac] = newChildrenDict[thisMac]
                    dictChanged = True

                    # note the changed ID in log
                    self.__networkLog.writeMessage(f"scan results: MAC address [{thisMac}] changed " +
                                                   f"Device ID from [{oldID}] to [{newID}]")

                # otherwise, check if this new mac's ID used to be connected with a different mac
                elif newChildrenDict[thisMac]['id'] in self.lookupByID:

                    #print (f"{self.__class__.__name__}: updateDisplays: Debug: [{thisMac}] same ID, different MAC")

                    thisID = newChildrenDict[thisMac]['id']
                    oldMac = self.lookupByID[thisID]
                    mb.showwarning(f"Warning: Device ID [{thisID}] used to be online with " +
                                   f"MAC address [{oldMac}] but now has MAC address [{thisMac}]. " +
                                   f"Previous settings and data will be discarded and everything " +
                                   f"loaded anew from the device.",
                                   parent=self.erl2context['root'])
                    self.childrenDict[thisMac] = newChildrenDict[thisMac]
                    dictChanged = True

                    # note the changed ID in log
                    self.__networkLog.writeMessage(f"scan results: Device ID [{thisID}] changed " +
                                                   f"MAC address from [{oldMac}] to [{thisMac}]")

                # the final alternative is that this is an entirely new MAC and ID
                else:

                    #print (f"{self.__class__.__name__}: updateDisplays: Debug: [{thisMac}] new MAC never seen before")

                    # no warning needed, just add it
                    self.childrenDict[thisMac] = newChildrenDict[thisMac]
                    dictChanged = True

                    # note the newly-found device in log
                    self.__networkLog.writeMessage(f"scan results: found Device ID [{self.childrenDict[thisMac]['id']}], " +
                                                   f"Type [{self.childrenDict[thisMac]['deviceType']}], " +
                                                   f"MAC address [{thisMac}], IP address [{self.childrenDict[thisMac]['ip']}]")

            # [ end of looping  through any new children ]

            # redo the list of sorted macs now that scan results have been processed
            self.sortedMacs = self.createSortedMacs()

            # rebuild the lookups to ensure old devices are no longer represented
            self.lookupByID, self.lookupByIP = self.createLookups()

            # by the way, create a new internal ID for anything that is missing one
            idsChanged = False
            for thisMac in self.sortedMacs:

                if 'internalID' not in self.childrenDict[thisMac]:

                    # eliminate symbols and spaces
                    adjustedID = re.sub('(^__*)|(__*$)','',re.sub('\W\W*','_',self.childrenDict[thisMac]['id']))

                    # find a sequence number that hasn't already been used
                    rpt = 0
                    while f"{adjustedID}_{rpt:03}" in self.allInternalIDs:
                        rpt += 1

                    # this will be this device's internal ID
                    self.childrenDict[thisMac]['internalID'] = f"{adjustedID}_{rpt:03}"
                    dictChanged = True

                    # remember that we've used this ID
                    self.allInternalIDs.append(self.childrenDict[thisMac]['internalID'])
                    idsChanged = True

            # if any changes, save objects to state file
            if dictChanged:
                self.erl2context['state'].set([('network','childrenDict',self.childrenDict)])
            if idsChanged:
                self.erl2context['state'].set([('network','allInternalIDs',self.allInternalIDs)])

        # [this is the end of the logic for processing new scan results]

        # [now update the module's display widgets]

        # default font
        fnt = 'Arial 14'

        # loop through widget types
        for wType in self.__netWidgets:

            # children widgets are a little different
            if wType == 'children':
                self.populateChildrenTables(currentTime=currentTime)

            else:
                # first, get info for drawing this label
                upd, fnt, fgd = self.getDisplayVals(wType, currentTime=currentTime)

                # loop through widgets of this type
                ind = 0
                found = False
                while ind < len(self.__netWidgets[wType]):

                    # look for, and delete, widgets that no longer exist
                    if ('ref' not in self.__netWidgets[wType][ind]
                            or not self.__netWidgets[wType][ind]['ref'].winfo_exists()):

                        # delete this list entry because its widget is gone
                        #print (f"{self.__class__.__name__}: updateDisplays: Debug: deleting list entry of type [{wType}]")
                        self.__netWidgets[wType].pop(ind)

                        # move on to next element in list
                        continue

                    # special case: update the image on the 'online' widget
                    if wType == 'online':
                        self.__netWidgets[wType][ind]['ref'].config(image=self.__onlineImages[upd])

                    # everything else is just a text label
                    else:
                        self.__netWidgets[wType][ind]['ref'].config(text=upd, font=fnt, foreground=fgd)

                    # continue stepping through the list
                    ind += 1

        # if asked to, schedule the next display update
        if scheduleNext:

            # update on schedule
            nextUpdateTime = nextIntervalTime(currentTime, self.__updateFrequency)
            delay = int((nextUpdateTime - currentTime.timestamp())*1000)

            # update the display widgets again after waiting an appropriate number of milliseconds
            if self.__afterUpdateDisplays is None:
                self.__afterUpdateDisplays = self.erl2context['conf']['system']['allWidgets'].pop()
                #print (f"{self.__class__.__name__}: Debug: scheduling updateDisplays: allWidgets length [{len(self.erl2context['conf']['system']['allWidgets'])}]")
            self.__afterUpdateDisplays.after(delay, self.updateDisplays)

    def rescanSubnet(self, event=None, init=False):

        if self.scanning():
            mb.showinfo(title='Rescan ERL2 Subnet',
                        message="Another scan is already running.",
                        parent=self.erl2context['root'])

        else:
            # ask for confirmation unless this is the first scan during initialization
            if init or (mb.askyesno(title='Rescan ERL2 Subnet',
                                    message="Are you sure you want to scan for new devices on the ERL2 subnet?",
                                    parent=self.erl2context['root'])):
                self.wrapperScan()

    def wrapperListen(self):

        # do this in a separate process thread
        self.__listenProcess = Process(target=subthreadListen,
                                       args=(self.__deviceAddresses[0]['IP'],
                                             self.__incomingQueue,
                                             self.__outgoingQueue,
                                             ))
        self.__listenProcess.start()
        self.__listenTime = dt.now(tz=tz.utc)

    def wrapperScan(self):

        # controller startup log message
        self.__networkLog.writeMessage('initiating subnet scan')

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

        # remember what time it is
        currentTime = dt.now(tz=tz.utc)

        # network check for tank-type devices
        if self.__deviceType == 'tank':

            # has it been more than 30s since the last network activity?
            if self.__lastActive is None or currentTime.timestamp() - self.__lastActive.timestamp() > 30:

                # if the listener was last restarted more than 60s ago
                if self.__listenTime is None or currentTime.timestamp() - self.__listenTime.timestamp() > 60:

                    # check if new network interfaces have come online
                    self.getAddresses()

                    # were any deviceAddresses found?
                    if len(self.__deviceAddresses) > 0:

                        # based on results of getAddresses(), chose an interface to listen on
                        self.chooseTankInterface()

                        # tank startup log message
                        self.__networkLog.writeMessage(f"Tank startup at interface [{self.__interface}], ip [{self.__ip}], mac [{self.__mac}]")

                        # kill off the old listener if it exists
                        if self.__listenProcess is not None and self.__listenProcess.is_alive():
                            self.__listenProcess.kill()

                        # start up the process that will listen for controller comms in a subthread
                        self.wrapperListen()

        # are there any new requests to process?
        if not self.__incomingQueue.empty():

            # loop through all pending requests
            while not self.__incomingQueue.empty():
                rq = self.__incomingQueue.get_nowait()
                #print (f"{self.__class__.__name__}: manageQueues: Debug: Received request [{rq.inb}] from [{rq.addr}]")

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
                        ts = dt.strptime(ts.decode(), DTFMT).replace(tzinfo=tz.utc)

                    print (f"{self.__class__.__name__}: manageQueues: Debug: unpacked request [{rq.inb}] from [{rq.addr}] to give timestamp [{ts}]")
                    rq.outb = pickle.dumps(self.__systemLog.exportLog(ts))

                # HANGUP!: terminate listener and let it start up naturally again later
                elif rq.inb == b"HANGUP!":

                    # kill off the forked process listening for connections
                    if self.__listenProcess is not None and self.__listenProcess.is_alive():
                        self.__listenProcess.kill()

                    # send acknowledgment
                    rq.outb = 'OKAY!'.encode()

                # unrecognized request: answer with error
                else:
                    rq.outb = ''.encode()

                    # log an error message
                    self.__networkLog.writeMessage(f"Error: Received request [{rq.inb}] from [{rq.addr}], not recognized")

                print (f"{self.__class__.__name__}: manageQueues: Debug: Received request [{rq.inb}] from [{rq.addr}], answered with [{getsizeof(rq.outb)}] bytes")

                # log the request and reply
                self.__networkLog.writeMessage(f"Received request [{rq.inb}] from [{rq.addr}], answered with [{getsizeof(rq.outb)}] bytes")

                # add reply to the outgoing queue
                self.__outgoingQueue.put(rq)

                # update time of last device comms
                self.__lastActive = dt.now(tz=tz.utc)
                self.erl2context['state'].set([('network','lastActive',self.__lastActive)])

        # are there any command results to process?
        if not self.__commandResultsQueue.empty():

            # remember if any changes were made to the children dictionary
            dictChanged = False

            # loop through all pending results
            while not self.__commandResultsQueue.empty():

                # retrieve the command results and figure out what mac address they're for
                rs = self.__commandResultsQueue.get_nowait()

                # can get_nowait() return something that isn't a request?
                if rs is not None and hasattr(rs, "addr"):
                    mac = self.lookupByIP[rs.addr]

                    print (f"{self.__class__.__name__}: manageQueues: Received reply to command " +
                           f"[{rs.command}] from [{rs.addr}], [{getsizeof(rs.replyString)}] bytes")

                    # no matter what type of comms, update the lastActive timestamp
                    self.childrenDict[mac]['lastActive'] = rs.replyTime
                    dictChanged = True

                    if rs.command == b"GETID":

                         # we'll want to compare new results against the old
                         # (if changes, trigger another full network scan)
                         pass

                    elif rs.command == b"GETTIME":

                        # there could be unpickling problems
                        try:

                            # unpack reply, which is a pickled datetime instance
                            deviceT = pickle.loads(rs.replyString)

                            # something odd is going on if the reply isn't a datetime
                            if type(deviceT) is not dt:
                                print (f"{self.__class__.__name__}: manageQueues: Error: HANGUP! because type(deviceT) is [{type(deviceT).__name__}], not datetime")

                                # comms are out of sync, so hang up the listing tank and try again later
                                self.sendCommand(mac, b"HANGUP!")

                            else:

                                # calculate difference in controller/device clocks
                                self.childrenDict[mac]['latency'] = (deviceT-rs.replyTime).total_seconds()
                                dictChanged = True
                                #print (f"{self.__class__.__name__}: manageQueues: Debug: updating latency for [{mac}] to [{self.childrenDict[mac]['latency']}]")

                        except (pickle.UnpicklingError, EOFError) as e:
                            print (f"{self.__class__.__name__}: manageQueues: Error: HANGUP! because [{e.__class__.__name__}] in [{rs.command}] reply")

                            # comms are out of sync, so hang up the listing tank and try again later
                            self.sendCommand(mac, b"HANGUP!")

                    elif rs.command == b"GETSTATE":

                        # there could be unpickling problems
                        try:

                            # answered with an Erl2State instance (pickled)
                            thisState = pickle.loads(rs.replyString)

                            # some cursory type checking
                            if type(thisState) is not Erl2State:
                                print (f"{self.__class__.__name__}: manageQueues: Error: HANGUP! because bad state instance [{type(thisState).__name__}] for [{mac}][{self.childrenDict[mac]['id']}]")

                                # comms are out of sync, so hang up the listing tank and try again later
                                self.sendCommand(mac, b"HANGUP!")

                            else:

                                # if the Erl2State instance hasn't been created yet
                                if mac not in self.childrenStates:
                                    self.childrenStates[mac] = Erl2State(internalID=self.childrenDict[mac]['internalID'],
                                                                         erl2context=self.erl2context)

                                # now assign the new state values to this child State instance
                                self.childrenStates[mac].assign(thisState)

                                # as a final step, refresh any associated Erl2Readout instances
                                if mac in self.childrenReadouts:
                                    self.childrenReadouts[mac].refreshDisplays()

                        except (pickle.UnpicklingError, EOFError) as e:
                            print (f"{self.__class__.__name__}: manageQueues: Error: HANGUP! because [{e.__class__.__name__}] in [{rs.command}] reply")

                            # comms are out of sync, so hang up the listing tank and try again later
                            self.sendCommand(mac, b"HANGUP!")

                    elif re.match(b'^GETLOG|', rs.command):

                        # there could be unpickling problems
                        try:

                            # answered with an export from an Erl2Log instance (pickled)
                            thisLog = pickle.loads(rs.replyString)
                            if type(thisLog) is not list:
                                print (f"{self.__class__.__name__}: manageQueues: Error: bad log instance [{type(thisLog).__name__}] for [{mac}][{self.childrenDict[mac]['id']}]")
                            else:

                                # if the Erl2Log instance hasn't been created yet
                                if mac not in self.childrenLogs:
                                    self.childrenLogs[mac] = Erl2Log(logType='device',
                                                                     logName=self.childrenDict[mac]['internalID'],
                                                                     erl2context=self.erl2context)

                                # now import the new log values to this child Erl2Log instance
                                self.childrenLogs[mac].importLog(thisLog)

                        except (pickle.UnpicklingError, EOFError) as e:
                            print (f"{self.__class__.__name__}: manageQueues: Error: HANGUP! because [{e.__class__.__name__}] in [{rs.command}] reply")

                            # comms are out of sync, so hang up the listing tank and try again later
                            self.sendCommand(mac, b"HANGUP!")

                    elif rs.command == b"HANGUP!":

                        # no action needed
                        pass

                    # unrecognized request: answer with error
                    else:
                        rq.outb = ''.encode()

                        # log an error message
                        self.__networkLog.writeMessage(f"Error: Received reply to command [{rs.command}] from [{rs.addr}], not recognized")

                    # log the reply
                    self.__networkLog.writeMessage(f"Received reply to command [{rs.command}] from [{rs.addr}], [{getsizeof(rs.replyString)}] bytes")

                    # update time of last device comms
                    self.__lastActive = dt.now(tz=tz.utc)
                    self.erl2context['state'].set([('network','lastActive',self.__lastActive)])

            # if any changes, save objects to state file
            if dictChanged:
                self.erl2context['state'].set([('network','childrenDict',self.childrenDict)])

        # call this method again after waiting 1s
        if self.__afterManageQueues is None:
            self.__afterManageQueues = self.erl2context['conf']['system']['allWidgets'].pop()
            #print (f"{self.__class__.__name__}: Debug: scheduling manageQueues: allWidgets length [{len(self.erl2context['conf']['system']['allWidgets'])}]")
        self.__afterManageQueues.after(1000, self.manageQueues)

    def pollChildren(self):

        # remember what time it is
        currentTime = dt.now(tz=tz.utc)

        # skip processing if we're scanning the network for new devices
        if not self.scanning():

            # loop through child devices
            for thisMac in self.sortedMacs:

                # get log (include info about timestamps already received)
                if 'logTime' not in self.childrenDict[thisMac] or currentTime.timestamp() - self.childrenDict[thisMac]['logTime'].timestamp() > 5.*60.: # five minutes
                    if thisMac in self.childrenLogs and self.childrenLogs[thisMac].latestTS is not None:
                        lastLog = self.childrenLogs[thisMac].latestTS.astimezone(tz.utc).strftime(DTFMT)
                    else:
                        lastLog = 'None'
                    self.sendCommand(thisMac, b"GETLOG" + b"|" + lastLog.encode())
                    self.childrenDict[thisMac]['logTime'] = currentTime

                # update latency (get time)
                elif 'timeTime' not in self.childrenDict[thisMac] or currentTime.timestamp() - self.childrenDict[thisMac]['timeTime'].timestamp() > 30.: # thirty seconds
                    self.sendCommand(thisMac, b"GETTIME")
                    self.childrenDict[thisMac]['timeTime'] = currentTime

                # get state
                elif 'stateTime' not in self.childrenDict[thisMac] or currentTime.timestamp() - self.childrenDict[thisMac]['stateTime'].timestamp() > 5.: # five seconds
                    self.sendCommand(thisMac, b"GETSTATE")
                    self.childrenDict[thisMac]['stateTime'] = currentTime

        # call this method again after waiting 5s
        if self.__afterPollChildren is None:
            self.__afterPollChildren = self.erl2context['conf']['system']['allWidgets'].pop()
            #print (f"{self.__class__.__name__}: Debug: scheduling pollChildren: allWidgets length [{len(self.erl2context['conf']['system']['allWidgets'])}]")
        self.__afterPollChildren.after(5000, self.pollChildren)

    def scanning(self):
        return self.__scanProcess is not None and self.__scanProcess.is_alive()

    def sendCommand(self, mac, command):

        #print (f"{self.__class__.__name__}: Debug: sendCommand([{mac}], [{command}]")

        # send command and give it a queue for its reply
        self.wrapperSendCommand(mac, command, self.__commandResultsQueue)

    # atexit.register() handler
    def atexitHandler(self):

        #print (f"{self.__class__.__name__}: atexitHangler: Debug: called")

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

    def createSortedMacs(self, childrenDict=None):

        # default is to use instance variable
        if childrenDict is None:
            childrenDict = self.childrenDict

        # complicated sort to properly order e.g. 'Tank 2' before 'Tank 13'
        # (append mac address after a linefeed in case tank ids are not unique)
        newSortedMacs = sorted(childrenDict, key=lambda x: re.sub(r'0*([0-9]{9,})',
                                                                  r'\1',
                                                                  re.sub(r'([0-9]+)',
                                                                         r'0000000000\1',
                                                                         childrenDict[x]['id']
                                                                        )
                                                                 ) + '\n' + x)

        return newSortedMacs

    def createLookups(self, childrenDict=None, sortedMacs=None):

        # default is to use instance variables
        if childrenDict is None:
            childrenDict = self.childrenDict
        if sortedMacs is None:
            sortedMacs = self.sortedMacs

        lookupByID = {}
        lookupByIP = {}
        for thisMac in sortedMacs:

            # add a new entry to the lookup dicts
            lookupByID[childrenDict[thisMac]['id']] = thisMac
            lookupByIP[childrenDict[thisMac]['ip']] = thisMac

        return lookupByID, lookupByIP

    def addWidgets(self,
                   typeLocs=[],
                   nameLocs=[],
                   interfaceLocs=[],
                   ipLocs=[],
                   macLocs=[],
                   statusLocs=[],
                   buttonLocs=[],
                   childrenLocs=[],
                   onlineLocs=[],
                   ):

        # pass each kind of widget to the create fn in turn
        if len(typeLocs)>0:      self.createWidgets('type',      typeLocs)
        if len(nameLocs)>0:      self.createWidgets('name',      nameLocs)
        if len(interfaceLocs)>0: self.createWidgets('interface', interfaceLocs)
        if len(ipLocs)>0:        self.createWidgets('ip',        ipLocs)
        if len(macLocs)>0:       self.createWidgets('mac',       macLocs)
        if len(statusLocs)>0:    self.createWidgets('status',    statusLocs)
        if len(childrenLocs)>0:  self.createWidgets('children',  childrenLocs)
        if len(onlineLocs)>0:    self.createWidgets('online',    onlineLocs)

        # a different method for network rescan buttons
        if len(buttonLocs)>0:
            self.addRescanButtons(buttonLocs)

    def addRescanButtons(self, buttonLocs=[]):

        # rescan button only makes sense for the controller
        if self.__deviceType == 'controller':

            # loop through locations
            for buttonLoc in buttonLocs:

                # read location parameter, set defaults if unspecified
                loc = locDefaults(loc=buttonLoc, modDefaults=self.modDefaults)

                # if the location is fully defined
                if 'parent' in loc:

                    # create a frame for the button
                    rescanFrame = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
                    rescanFrame.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                                     padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])

                    # frame within the frame? for placement (pad with side frames to force it to center)
                    f0 = ttk.Frame(rescanFrame) #, padding='0', relief='solid', borderwidth=1)
                    f0.grid(row=0, column=0, sticky='nesw')
                    f1 = ttk.Frame(rescanFrame) #, padding='0', relief='solid', borderwidth=1)
                    f1.grid(row=0, column=1, sticky='nesw')
                    f2 = ttk.Frame(rescanFrame) #, padding='0', relief='solid', borderwidth=1)
                    f2.grid(row=0, column=2, sticky='nesw')
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

    def createWidgets(self, widgetType, locations):

        # remember if we created any new children widgets
        newChildren = False

        # nothing to do if locations is empty
        if locations is None or len(locations) == 0:
            return

        # first, get info for drawing this label
        upd, fnt, fgd = self.getDisplayVals(widgetType)

        # make sure there's already a list for this widgetType
        if widgetType not in self.__netWidgets:
            self.__netWidgets[widgetType] = []

        # loop through all requested locations
        for l in locations:

            # apply default location parameters
            loc = locDefaults(l, modDefaults=self.modDefaults)

            # loop through all prior widget definitions of this type
            for wDef in self.__netWidgets[widgetType]:

                # make sure this is an active widget
                if 'ref' in wDef and wDef['ref'].winfo_exists():

                    # if the requested location is already in the list
                    if loc == wDef['loc']:
                        print (f"{self.__class__.__name__}: createWidgets({widgetType}): Debug: found matching location")
                        break

            # for/else is executed only if we didn't 'break'
            else:

                ## create the display widget's base frame as a child of its parent
                #f = ttk.Frame(loc['parent'], padding='0 0', relief='solid', borderwidth=1)
                #f.grid(row=loc['row'], column=loc['column'], padx='2', pady='0', sticky='nw')

                # children widgets are a little different
                if widgetType == 'children':

                    # create an empty Frame widget to hold the table of children details
                    f = ttk.Frame(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'])
                    f.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'],
                           padx=loc['padx'], pady=loc['pady'], sticky=loc['sticky'])

                    # add this location and widget reference to the list
                    self.__netWidgets[widgetType].append({'loc':loc, 'ref':f})

                    # add to internal widget list if standalone
                    if self.__standalone:
                        self.erl2context['conf']['system']['allWidgets'].append(f)

                    # this means we've created new children widgets
                    newChildren = True

                # all other updatable widgets are just plain labels
                else:

                    # note that online widgets are images, not text
                    if widgetType == 'online':

                        # add a Label widget to show the current value
                        l = ttk.Label(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'],
                            image=self.__onlineImages[upd])
                        l.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'], sticky=loc['sticky'])

                    # other widgets are text labels
                    else:

                        # add a Label widget to show the current value
                        l = ttk.Label(loc['parent'], padding=loc['padding'], relief=loc['relief'], borderwidth=loc['borderwidth'],
                            text=upd, font=fnt, foreground=fgd)
                        l.grid(row=loc['row'], column=loc['column'], rowspan=loc['rowspan'], columnspan=loc['columnspan'], sticky=loc['sticky'])

                    # add this location and widget reference to the list
                    self.__netWidgets[widgetType].append({'loc':loc, 'ref':l})

                    # add to internal widget list if standalone
                    if self.__standalone:
                        self.erl2context['conf']['system']['allWidgets'].append(l)

        # if there are new children, we should populate those tables
        if newChildren:
            self.populateChildrenTables()

    def getDisplayVals(self, widgetType=None, currentTime=None):

        # we only need currentTime, if not supplied, for status and online
        if widgetType in ['status', 'online'] and currentTime is None:
            currentTime = dt.now(tz=tz.utc)

        # default update text
        upd = '--'

        # default font
        fnt = 'Arial 14'

        # default color (may be system dependent)
        fgd = ''

        if widgetType == 'type':
            upd = self.__deviceType
        elif widgetType == 'name':
            upd = self.__id
        elif widgetType == 'interface':
            upd = self.__interface
        elif widgetType == 'ip':
            upd = self.__ip
        elif widgetType == 'mac':
            upd = self.__mac

        # more logic for status and online widgets (based on lastActive and lapseTime)
        elif widgetType in ['status', 'online']:

            # defaults
            online = False
            upd = 'never'

            # adjust the formatting if the communications have gone quiet
            if self.__lastActive is None or currentTime.timestamp() - self.__lastActive.timestamp() > self.__lapseTime:
                fnt = 'Arial 14 bold'
                fgd = '#A93226' # red
            else:
                fnt = 'Arial 14'
                fgd = '#1C4587' # blue
                online = True

            # datetimes need to be formatted for display
            if widgetType == 'status' and self.__lastActive is not None:
                upd = self.__lastActive.astimezone(self.__timezone).strftime(self.__dtFormat)

            # but 'online' just returns 0 for offline and 1 for online
            elif widgetType == 'online':
                upd = int(online)

            #print (f"{self.__class__.__name__}: getDisplayVals({widgetType}): Debug: "
            #       f"upd [{upd}], fnt [{fnt}], fgd [{fgd}], "
            #       f"currentTime [{currentTime}], lastActive [{self.__lastActive}]")

        # return all three parameters
        return upd, fnt, fgd

    def populateChildrenTables(self, currentTime=None):

        # nothing to do if there aren't any children widgets
        if 'children' not in self.__netWidgets or len(self.__netWidgets['children']) == 0:
            return

        # all of this code deals with children widgets
        wType = 'children'

        # current time, if not supplied
        if currentTime is None:
            currentTime = dt.now(tz=tz.utc)

        # loop through children widgets
        ind = 0
        while ind < len(self.__netWidgets[wType]):

            # look for, and delete, widgets that no longer exist
            if ('ref' not in self.__netWidgets[wType][ind]
                    or not self.__netWidgets[wType][ind]['ref'].winfo_exists()):

                # delete this list entry because its widget is gone
                #print (f"{self.__class__.__name__}: populateChildrenTables: Debug: deleting list entry of type [{wType}]")
                self.__netWidgets[wType].pop(ind)

                # move on to next element in list
                continue

            # save some typing below
            w = self.__netWidgets[wType][ind]['ref']

            # only draw the children table headers once
            if ('headers' not in self.__netWidgets[wType][ind]
                    or not self.__netWidgets[wType][ind]['headers']):

                #print (f"{self.__class__.__name__}: populateChildrenTable: Debug: drawing headers")
                self.__netWidgets[wType][ind]['headers'] = True

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

            # this next part only makes sense if any children were found
            if len(self.childrenDict) > 0:

                thisrow = 0
                for mac in self.sortedMacs:

                    thisrow += 1

                    # special formatting for lastActive
                    lastA = self.childrenDict[mac]['lastActive']
                    upd = lastA.astimezone(self.__timezone).strftime(self.__dtFormat)
                    if lastA is None or currentTime.timestamp() - lastA.timestamp() > self.__lapseTime:
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

                        #print (f"{self.__class__.__name__}: updateDisplays: Debug: THIS IS A NEW ROW")

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
                        #print (f"{self.__class__.__name__}: updateDisplays: Debug: FOUND AN EXISTING ROW [{w.grid_slaves(row=thisrow,column=4)}]")
                        w.grid_slaves(row=thisrow,column=0)[0].grid_slaves(row=0,column=0)[0].config(text=self.childrenDict[mac]['id'])
                        w.grid_slaves(row=thisrow,column=1)[0].grid_slaves(row=0,column=0)[0].config(text=self.childrenDict[mac]['ip'])
                        w.grid_slaves(row=thisrow,column=2)[0].grid_slaves(row=0,column=0)[0].config(text=mac)
                        w.grid_slaves(row=thisrow,column=3)[0].grid_slaves(row=0,column=0)[0].config(text=upd, font=fnt, foreground=fgd)
                        w.grid_slaves(row=thisrow,column=4)[0].grid_slaves(row=0,column=0)[0].config(text=lat)

            # continue stepping through the list
            ind += 1

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Network',font='Arial 30 bold').grid(row=0,column=0,columnspan=2)

    ttk.Label(root,text='Type:',font='Arial 14 bold',justify='right').grid(row=1,column=0,sticky='nes')
    ttk.Label(root,text='Name:',font='Arial 14 bold',justify='right').grid(row=2,column=0,sticky='nes')
    ttk.Label(root,text='Network interface:',font='Arial 14 bold',justify='right').grid(row=3,column=0,sticky='nes')
    ttk.Label(root,text='IP address:',font='Arial 14 bold',justify='right').grid(row=4,column=0,sticky='nes')
    ttk.Label(root,text='MAC address:',font='Arial 14 bold',justify='right').grid(row=5,column=0,sticky='nes')
    ttk.Label(root,text='Last network comms:',font='Arial 14 bold',justify='right').grid(row=6,column=0,sticky='nes')

    childrenFrame = ttk.Frame(root)
    childrenFrame.grid(row=7,column=0,columnspan=2)

    network = Erl2Network(standalone=True,
                          typeLocs=[{'parent':root,'row':1,'column':1}],
                          nameLocs=[{'parent':root,'row':2,'column':1}],
                          interfaceLocs=[{'parent':root,'row':3,'column':1}],
                          ipLocs=[{'parent':root,'row':4,'column':1}],
                          macLocs=[{'parent':root,'row':5,'column':1}],
                          statusLocs=[{'parent':root,'row':6,'column':1}],
                          buttonLocs=[{'parent':root,'row':8,'column':0,'columnspan':2}],
                          childrenLocs=[{'parent':childrenFrame,'row':0,'column':0}],
                          erl2context={'root':root},
                          )

    # set things up for graceful termination
    atexit.register(network.atexitHandler)

    root.mainloop()

if __name__ == "__main__": main()

