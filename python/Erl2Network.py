#! /usr/bin/python3

import netifaces
import re
import selectors
import socket
import tkinter as tk
import types
from tkinter import ttk
from Erl2Config import Erl2Config

class Erl2Network():

    # ports to communicate on
    SERVERPORT = 65432
    CLIENTPORT = 65433

    def __init__(self,
                 erl2context={}):

        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # read these useful parameters from Erl2Config
        self.__type = self.erl2context['conf']['device']['type']
        self.__id = self.erl2context['conf']['device']['id']

        # details of the network connection(s)
        self.__counter = 0
        self.__ifaddresses = {}
        self.__addrChange = False

        # determine what IP address(es) to use
        self.getAddresses()

        # if controller, start listening on connection(s)
        if self.__type == 'controller':
            self.listen()

        # if tank, try to reach controller; keep trying until sucessful

    def getAddresses(self):

        # all potential interface addresses, controller and/or tank
        candidates = {}

        # come up with a list of all possible IPv4 interface addresses
        for i in netifaces.interfaces():

            # this is a dict of address types; AF_INET is IPv4
            ifList = netifaces.ifaddresses(i)
            if netifaces.AF_INET in ifList.keys():

                # this is a list of address dicts (can be more than one IP per hw interface)
                for adr in ifList[netifaces.AF_INET]:

                    # only check dicts with 'addr' key
                    if 'addr' in adr.keys():

                        # skip loopback/localhost address
                        if adr['addr'] != '127.0.0.1':

                            # for controllers, add addresses ending in .1
                            if self.__type == 'controller' and re.search('\.1+$',adr['addr']) is not None:
                                candidates[adr['addr']] = 'controller'

                            # for tanks, substitute that last .xxx part of the address with .1
                            if self.__type == 'tank' and re.search('\.1+$',adr['addr']) is None:
                                candidates[adr['addr']] = 'tank'

        # loop through old addresses and delete them if the interface is no longer listed
        for adr in self.__ifaddresses.keys():
            if adr not in candidates:
                print (f"{self.__class__.__name__}: Debug: getAddresses() deleting [{adr}][{self.__ifaddresses[adr]['type']}]")
                del self.__ifaddresses[adr]
                self.__addrChange = True

        # loop through new addresses and add them if not already listed
        for adr in candidates.keys():
            if adr not in self.__ifaddresses:
                self.__ifaddresses[adr] = {'type':candidates[adr]}
                print (f"{self.__class__.__name__}: Debug: getAddresses() adding [{adr}][{self.__ifaddresses[adr]['type']}]")
                self.__addrChange = True

    def handshake(self):

        # send 'hello' and listen for reply
        pass

    def getId(self):

        # send 'id' and listen for type/id reply
        pass

    def send(self):

        # construct some kind of message (log data, status data, data query, command)
        pass

    def listen(self):

        # whether controller or tank, always listen for comms from the other side
        pass

        # decide what to do when a message is received...
        # 1. if hello, acknowledge
        # 2. if command, carry it out and reply with status update
        # 3. if log data, store + update displays
        # 4. if query, answer

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Network',font='Arial 30 bold').grid(row=0,column=0,columnspan=3)

    network = Erl2Network()

    root.mainloop()

if __name__ == "__main__": main()

