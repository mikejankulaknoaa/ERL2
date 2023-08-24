#! /usr/bin/python3

from csv import DictReader
from datetime import datetime as dt
from datetime import timedelta as td
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk
from Erl2Config import Erl2Config

#matplotlib.use('TkAgg')

class Erl2Plot():

    def __init__(self,
                 plotLoc={},
                 figsize=(5,3),
                 displayParameter=None,
                 plotData=[],
                 erl2context={}):

        # save the Erl2Plot-specific parameters in attributes
        self.__plotLoc = plotLoc
        self.__figsize = figsize
        self.__displayParameter = displayParameter
        self.__plotData = plotData
        self.erl2context = erl2context

        # attributes associated with plotting activity
        self.__fig = None
        self.__timeRange = td(days=-1)

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()
            #if 'tank' in self.erl2context['conf'].sections() and 'id' in self.erl2context['conf']['tank']:
            #    print (f"{self.__class__.__name__}: Debug: Tank Id is [{self.erl2context['conf']['tank']['id']}]")

        # x axis limits
        currentTime = dt.now()
        dayAgo = currentTime + self.__timeRange

        ## try to import some junk data if nothing was passed
        #if self.__displayParameter == 'junk' and self.__plotData == []:

        #    # read in one day's worth of data from a test file on the system
        #    with open(self.erl2context['conf']['system']['rootDir'] + '/test/temp.dat', 'r', newline='') as f:
        #        r = DictReader(f, dialect='unix')
        #        self.__plotData.append({'name':'temperature', 'data':list(r)})

        #    # create a fake Erl2Log instance
        #    log = Erl2Log(self.erl2context)

        #    # adjust the displayParameter to match what's in the test file
        #    self.__displayParameter = 'temp.degC'

        #    # fudge the time axis so that the file's data will be displayed
        #    currentTime = dt.strptime("2023-08-14 08:45:01","%Y-%m-%d %H:%M:%S")
        #    dayAgo = currentTime + self.__timeRange

        # override default 'math' font type for $...$ expressions (e.g. $CO_2$), which is italics
        matplotlib.rcParams["mathtext.default"] = 'regular'

        # specify style
        #plt.style.use('classic')
        #plt.style.use('ggplot')
        #plt.style.use('bmh')
        #plt.style.use('fivethirtyeight')
        #plt.style.use('seaborn-v0_8')
        plt.style.use('seaborn-v0_8-darkgrid')

        # create main Figure
        self.__fig = plt.figure(figsize=self.__figsize, dpi=100, facecolor='#dbdbdb')

        # loop through subplots
        for ind in range(len(self.__plotData)):

            # create the subplot
            if ind == 0:
                self.__fig.add_subplot(len(self.__plotData)+1, 1, (1,2), facecolor='#dbdbdb')
            else:
                self.__fig.add_subplot(len(self.__plotData)+1, 1, ind+2, sharex=self.__fig.axes[0], facecolor='#dbdbdb')

        # pause here to add all the plot lines
        self.updatePlotLines()

        # loop through subplots again
        for ind in range(len(self.__plotData)):

            # determine line specs
            specs = self.getSpecs(self.__plotData[ind]['name'])

            # format the axes?
            self.__fig.axes[ind].xaxis.set_major_formatter(mdates.DateFormatter('%H'))
            self.__fig.axes[ind].set_xlim(dayAgo, currentTime)

            # disable vertical grid lines
            self.__fig.axes[ind].grid(visible=False, which='both', axis='x')

            # customize axes: this is the x axis of the very last subplot in the figure
            if ind < len(self.__plotData)-1:

                # disable tickmarks and labelling
                self.__fig.axes[ind].tick_params(axis='x',          # changes apply to the x-axis
                                                 which='both',      # both major and minor ticks are affected
                                                 bottom=False,      # ticks along the bottom edge are off
                                                 top=False,         # ticks along the top edge are off
                                                 labelbottom=False) # labels along the bottom edge are off

            # customize axes: this is the y axis of any subplot other than the first
            if ind > 0:

                # don't allow the controls' Y axis range to vary
                if 'yLimit' in specs and specs['yLimit'] is not None:
                    self.__fig.axes[ind].set_ylim(0, specs['yLimit'])

                # disable tickmarks and labelling
                self.__fig.axes[ind].tick_params(axis='y',          # changes apply to the y-axis
                                                 which='both',      # both major and minor ticks are affected
                                                 left=False,        # ticks along the left edge are off
                                                 right=False,       # ticks along the right edge are off
                                                 labelleft=False)   # labels along the left edge are off

                # disable horizontal grids for the controls
                self.__fig.axes[ind].grid(visible=False, which='both', axis='y')

            # axes labels
            #print (f"{__class__.__name__}: Debug: name [{self.__plotData[ind]['name']}], specs [{specs}]")
            if 'yLabel' in specs and specs['yLabel'] is not None:
                self.__fig.axes[ind].set_ylabel(specs['yLabel'], rotation=0, labelpad=15, y=0.0)

            # eliminate excessive whitespace around plots
            #plt.subplots_adjust(left=0.12, right=0.99, top=0.98, bottom=0.12)
            plt.subplots_adjust(left=0.12, right=0.99, top=0.96, bottom=0.12)

        # place the plot on the window
        self.canvas = FigureCanvasTkAgg(self.__fig,self.__plotLoc['parent'])
        plt.draw()
        self.canvas.get_tk_widget().grid(row=self.__plotLoc['row'],column=self.__plotLoc['column'],sticky='nwse')

        # make sure plot canvas is weighted properly in parent frame
        self.__plotLoc['parent'].rowconfigure(0,weight=1)
        self.__plotLoc['parent'].columnconfigure(0,weight=1)

    def updatePlotLines(self):

        # loop through subplots
        for ind in range(len(self.__plotData)):

            # determine line specs
            specs = self.getSpecs(self.__plotData[ind]['name'])

            # convert log history into a pandas dataframe
            data = pd.DataFrame(self.__plotData[ind]['log'].history)

            #print (f"{__class__.__name__}: Debug: updatePlotLines() [{self.__displayParameter}][{self.__plotData[ind]['name']}] length [{len(data)}]")

            # verify that the parameter we're trying to draw actually exists in the log file
            if 'yName' in specs and specs['yName'] in data:

                # convert x and y axis columns into datetime and numeric types, respectively
                data['Timestamp.Local'] = pd.to_datetime(data['Timestamp.Local'])
                data[specs['yName']] = pd.to_numeric(data[specs['yName']])

                # eliminate any missing or invalid values
                data = data[data['Timestamp.Local'].notnull()]
                data = data[data[specs['yName']].notnull()]

                data.set_index('Timestamp.Local', inplace=True)

                # only proceed if the dataframe has any rows in it
                if len(data) > 0:

                    # divide into plot segments where there are >60min gaps; adapted from
                    # https://towardsdatascience.com/plot-organization-in-matplotlib-your-one-stop-guide-if-you-are-reading-this-it-is-probably-f79c2dcbc801

                    # Convert threshold to nanoseconds
                    threshold_ns = 60 * 60 * 1e9

                    # Find the gaps larger than the threshold
                    gaps = data.index.to_series().diff() > pd.Timedelta(threshold_ns)

                    # Split the data into segments at the gaps
                    splits = (data[gaps].index.to_series() - pd.Timedelta(threshold_ns)).tolist()
                    segments = np.split(data, data.index.searchsorted(splits))

                    # special case: if there are fewer line segments now than in the past, delete the earliest ones
                    while len(self.__fig.axes[ind].lines) > 0 and len(self.__fig.axes[ind].lines) > len(segments):
                        #print (f"{__class__.__name__}: Debug: updatePlotLines(): DELETING [{self.__displayParameter}][{self.__plotData[ind]['name']}] one line")
                        self.__fig.axes[ind].lines[0].remove()

                    # Plot each segment separately
                    line = 0
                    for segment in segments:

                        # if this line segment exists, update its data
                        if len(self.__fig.axes[ind].lines) >= line+1:

                            #if self.__plotData[ind]['name'] in ['to.raise','to.lower','virtualtemp','temperature']:
                            #    print (f"{__class__.__name__}: Debug: updatePlotLines(): UPDATING [{self.__displayParameter}][{self.__plotData[ind]['name']}] line [{line}] length [{len(segment)}]")
                            self.__fig.axes[ind].lines[line].set_data(segment.index, segment[specs['yName']])

                        # otherwise, this is a new line segment to be added
                        else:

                            #if self.__plotData[ind]['name'] in ['to.raise','to.lower','virtualtemp','temperature']:
                            #    print (f"{__class__.__name__}: Debug: updatePlotLines(): CREATING [{self.__displayParameter}][{self.__plotData[ind]['name']}] line [{line}] length [{len(segment)}]")
                            self.__fig.axes[ind].plot(segment.index, segment[specs['yName']], color=specs['color'])

                        # increment line for next loop
                        line += 1

    def updatePlot(self):

        # x axis limits
        currentTime = dt.now()
        dayAgo = currentTime + self.__timeRange

        self.updatePlotLines()

        # loop through subplots
        for ind in range(len(self.__plotData)):

            # update the time axes limits
            self.__fig.axes[ind].set_xlim(dayAgo, currentTime)

        self.canvas.draw()
        plt.draw()

    def getSpecs(self, name='generic'):

        # hardcode the appearance of certain parameters
        if name == 'to.raise':
            return {'yName':'On (seconds)',
                    'yLabel':'Heat',
                    'yLimit':300.,
                    'color':'red'}
        if name == 'to.lower':
            return {'yName':'On (seconds)',
                    'yLabel':'Chill',
                    'yLimit':300.,
                    'color':'blue'}
        if name == 'mfc.air':
            return {'yName':'Average Flow Setting',
                    'yLabel':'Air',
                    'yLimit':5000.,
                    'color':'deepskyblue'}
        if name == 'mfc.co2':
            return {'yName':'Average Flow Setting',
                    #'yLabel':u'CO\u2082',
                    'yLabel':'$CO_2$',
                    'yLimit':20.,
                    'color':'grey'}
        if name == 'mfc.n2':
            return {'yName':'Average Flow Setting',
                    #'yLabel':u'N\u2082',
                    'yLabel':'$N_2$',
                    'yLimit':5000.,
                    'color':'limegreen'}

        # default appearance
        return {'yName':self.__displayParameter,
                'yLabel':None,
                'yLimit':None,
                'color':'black'}

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Plot',font='Arial 30 bold').grid(row=0,column=0)

    f = ttk.Frame(root)
    f.grid(row=1,column=0,sticky='nesw')

    plot = Erl2Plot(plotLoc={'parent':f,'row':0,'column':0},
                    displayParameter='junk')

    ttk.Button(f,text='Exit',command=lambda:tk.Tk.quit(root)).grid(row=2,column=0)

    root.mainloop()

if __name__ == "__main__": main()

