#! /usr/bin/python3

import megaind as ind
from Erl2Toggle import Erl2Toggle

class Erl2Chiller(Erl2Toggle):

    def __init__(self,
                 displayLocs=[],
                 buttonLocs=[],
                 displayImages=['button-grey-30.png','button-blue-30.png'],
                 buttonImages=['radio-off-blue-30.png','radio-on-blue-30.png'],
                 label='Chiller',
                 stack=0,
                 channel=None,
                 erl2conf=None,
                 img=None):

        # call the Erl2Toggle class's constructor
        super().__init__(type='chiller',
                         displayLocs=displayLocs,
                         buttonLocs=buttonLocs,
                         displayImages=displayImages,
                         buttonImages=buttonImages,
                         label=label,
                         erl2conf=erl2conf,
                         img=img)

        # private attributes specific to Erl2Chiller
        self.__stack = stack
        self.__channel = channel

        # the default output channel for the ERL2 chiller solenoid is 1
        if self.__channel is None:
            self.__channel = 1

        # start up the timing loop to log chiller-related metrics to a log file
        self.updateLog()

    def changeHardwareState(self):

        # apply the new state to the chiller solenoid hardware
        #print (f"{self.__class__.__name__}: Debug: changing to state [{self.state}] on channel [{self.__channel}]")

        if self.state:
            # turn on chiller -- set to 100%
            ind.setOdPWM(self.__stack,self.__channel,100)
        else:
            # turn off chiller -- set to 0%
            ind.setOdPWM(self.__stack,self.__channel,0)

def main():

    root = Tk()
    chiller = Erl2Chiller(root)
    root.mainloop()

if __name__ == "__main__": main()

