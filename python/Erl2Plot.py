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
                 statsLoc={},
                 figsize=(5,3),
                 displayData=[],
                 displaySpecs=[],
                 displayDecimals=None,
                 erl2context={}):

        # save the Erl2Plot-specific parameters in attributes
        self.__plotLoc = plotLoc
        self.__statsLoc = statsLoc
        self.__figsize = figsize
        self.__displayData = displayData
        self.__displaySpecs = displaySpecs
        self.__displayDecimals = displayDecimals
        self.erl2context = erl2context

        # read in the system configuration file if needed
        if 'conf' not in self.erl2context:
            self.erl2context['conf'] = Erl2Config()

        # associated statistics displays
        self.__meanDisplay = None
        self.__stdDisplay = None

        # attributes associated with plotting activity
        self.__fig = None
        self.__timeRange = td(days=-1)

        # x axis limits
        currentTime = dt.now()
        dayAgo = currentTime + self.__timeRange

        # override default 'math' font type for $...$ expressions (e.g. $CO_2$), which is italics
        matplotlib.rcParams["mathtext.default"] = 'regular'

        # some styles previously considered
        #plt.style.use('classic')
        #plt.style.use('ggplot')
        #plt.style.use('bmh')
        #plt.style.use('fivethirtyeight')
        #plt.style.use('seaborn-v0_8')
        #plt.style.use('seaborn-v0_8-darkgrid')

        # the matplotlib styles may have slightly different names on different platforms
        avStyles = plt.style.available

        # narrow down the list of styles in stages
        bestStyles = [ x for x in avStyles if 'seaborn' in x ]
        if len(bestStyles):
            avStyles = bestStyles
            bestStyles = [ x for x in avStyles if 'dark' in x ]
            if len(bestStyles):
                avStyles = bestStyles
                bestStyles = [ x for x in avStyles if 'darkgrid' in x ]

        # final style selection
        if len(bestStyles):
            plt.style.use(bestStyles[0])
        else:
            plt.style.use('classic')

        # set up the plot statistics frame
        if 'parent' in self.__statsLoc:

            ttk.Label(self.__statsLoc['parent'], text='Mean:', font='Arial 14'
                #, relief='solid', borderwidth=1
                ).grid(row=0, column=0, sticky='nw')
            ttk.Label(self.__statsLoc['parent'], text='Stdev:', font='Arial 14'
                #, relief='solid', borderwidth=1
                ).grid(row=1, column=0, sticky='nw')
            ttk.Label(self.__statsLoc['parent'], text='Target dev:', font='Arial 14'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=0, sticky='nw')

            self.__meanDisplay = ttk.Label(self.__statsLoc['parent'], text='--', font='Arial 14 bold', foreground='#1C4587'
                #, relief='solid', borderwidth=1
                )
            self.__meanDisplay.grid(row=0, column=1, padx='2 0', sticky='ne')
            self.__stdDisplay = ttk.Label(self.__statsLoc['parent'], text='--', font='Arial 14 bold', foreground='#1C4587'
                #, relief='solid', borderwidth=1
                )
            self.__stdDisplay.grid(row=1, column=1, padx='2 0', sticky='ne')

            ttk.Label(self.__statsLoc['parent'], text='--', font='Arial 14 bold', foreground='#A93226'
                #, relief='solid', borderwidth=1
                ).grid(row=2, column=1, padx='2 0', sticky='ne')

        # create main Figure
        self.__fig = plt.figure(figsize=self.__figsize, dpi=100, facecolor='#dbdbdb')

        # loop through subplots
        for ind in range(len(self.__displaySpecs)):

            # create the subplot
            if ind == 0:
                self.__fig.add_subplot(len(self.__displaySpecs)+1, 1, (1,2), facecolor='#dbdbdb')
            else:
                self.__fig.add_subplot(len(self.__displaySpecs)+1, 1, ind+2, sharex=self.__fig.axes[0], facecolor='#dbdbdb')

        # pause here to add all the plot lines
        self.updatePlotLines()

        # loop through subplots again
        for ind in range(len(self.__displaySpecs)):

            # determine line specs
            specs = self.__displaySpecs[ind]

            # format the axes?
            self.__fig.axes[ind].xaxis.set_major_formatter(mdates.DateFormatter('%H'))
            self.__fig.axes[ind].set_xlim(dayAgo, currentTime)

            # disable vertical grid lines
            self.__fig.axes[ind].grid(visible=False, which='both', axis='x')

            # customize axes: this is the x axis of the very last subplot in the figure
            if ind < len(self.__displaySpecs)-1:

                # disable tickmarks and labelling
                self.__fig.axes[ind].tick_params(axis='x',          # changes apply to the x-axis
                                                 which='both',      # both major and minor ticks are affected
                                                 bottom=False,      # ticks along the bottom edge are off
                                                 top=False,         # ticks along the top edge are off
                                                 labelbottom=False) # labels along the bottom edge are off

            # customize axes: this is the y axis of any subplot other than the first
            if ind > 0:

                # don't allow the controls' Y axis range to vary
                if 'yLimit' in self.__displaySpecs[ind] and self.__displaySpecs[ind]['yLimit'] is not None:
                    self.__fig.axes[ind].set_ylim(0, self.__displaySpecs[ind]['yLimit'])

                # disable tickmarks and labelling
                self.__fig.axes[ind].tick_params(axis='y',          # changes apply to the y-axis
                                                 which='both',      # both major and minor ticks are affected
                                                 left=False,        # ticks along the left edge are off
                                                 right=False,       # ticks along the right edge are off
                                                 labelleft=False)   # labels along the left edge are off

                # disable horizontal grids for the controls
                self.__fig.axes[ind].grid(visible=False, which='both', axis='y')

            # axes labels
            #print (f"{__class__.__name__}: Debug: name {self.__displaySpecs[ind]}")
            if 'yLabel' in self.__displaySpecs[ind] and self.__displaySpecs[ind]['yLabel'] is not None:
                self.__fig.axes[ind].set_ylabel(self.__displaySpecs[ind]['yLabel'], rotation=0, labelpad=15, y=0.0)

            # eliminate excessive whitespace around plots
            #plt.subplots_adjust(left=0.12, right=0.99, top=0.98, bottom=0.12)
            plt.subplots_adjust(left=0.12, right=0.99, top=0.96, bottom=0.12)

        # place the plot on the window
        self.canvas = FigureCanvasTkAgg(self.__fig,self.__plotLoc['parent'])
        plt.draw()
        self.canvas.get_tk_widget().grid(row=self.__plotLoc['row'],column=self.__plotLoc['column'],sticky='nesw')

        # make sure plot canvas is weighted properly in parent frame
        self.__plotLoc['parent'].rowconfigure(0,weight=1)
        self.__plotLoc['parent'].columnconfigure(0,weight=1)

    def updatePlotLines(self):

        # keep track of whether stats were updated
        statsUpdated = False

        # loop through subplots
        for ind in range(len(self.__displaySpecs)):

            # determine line specs
            specs = self.__displaySpecs[ind]

            # assume we're using the first and only displayData object for all plotLines
            dataInd = 0

            # but sometimes there is a different displayData object for every plotLine
            if 0 < ind < len(self.__displayData):
                dataInd = ind

            # convert log history into a pandas dataframe
            data = pd.DataFrame(self.__displayData[dataInd].history)

            #print (f"{__class__.__name__}: Debug: updatePlotLines() [{self.__displaySpecs[ind]['yName']}][{self.__displaySpecs[ind]['yParameter]}] length [{len(data)}]")

            # verify that the parameter we're trying to draw actually exists in the log file
            if 'yParameter' in self.__displaySpecs[ind] and self.__displaySpecs[ind]['yParameter'] in data:

                # save some typing
                yParameter = self.__displaySpecs[ind]['yParameter']

                # convert x and y axis columns into datetime and numeric types, respectively
                data['Timestamp.Local'] = pd.to_datetime(data['Timestamp.Local'])
                data[yParameter] = pd.to_numeric(data[yParameter],errors='coerce')

                # eliminate any missing or invalid values
                data = data[data['Timestamp.Local'].notnull()]
                data = data[data[yParameter].notnull()]

                data.set_index('Timestamp.Local', inplace=True)

                # only proceed if the dataframe has any rows in it
                if len(data) > 0:

                    # divide into plot segments where there are >60min gaps; adapted from
                    # https://towardsdatascience.com/plot-organization-in-matplotlib-your-one-stop-guide-if-you-are-reading-this-it-is-probably-f79c2dcbc801

                    # Convert threshold to nanoseconds
                    threshold_ns = 60 * 60 * 1e9

                    # Find the gaps larger than the threshold
                    gaps = data.index.to_series().diff() > pd.Timedelta(threshold_ns)
                    trueGaps = gaps[gaps==True]

                    # this next bit is to avoid using np.split() on a DataFrame, which is deprecated (use .iloc instead)

                    ## Split the data into segments at the gaps (don't convert to list)
                    ##splits = (data[gaps].index.to_series() - pd.Timedelta(threshold_ns)).tolist()
                    #splits = (data[gaps].index.to_series() - pd.Timedelta(threshold_ns))
                    #segments = np.split(data, data.index.searchsorted(splits))

                    # loop through split points
                    lastInd = 0
                    segments = []
                    for gInd in range(len(trueGaps)):

                        # what is positional index?
                        pInd = data.index.get_loc(trueGaps.index[gInd])

                        # grab a slice of the data array
                        slc = data.iloc[lastInd:pInd]

                        # add to segments if non-empty
                        if len(slc) > 0:
                            segments.append(slc)

                        # remember this index for next time through the loop
                        lastInd = pInd

                    # last slice of the array (if non-empty)
                    if len(data.iloc[lastInd:]) > 0:
                        segments.append(data.iloc[lastInd:])

                    # special case: if there are fewer line segments now than in the past, delete the earliest ones
                    while len(self.__fig.axes[ind].lines) > 0 and len(self.__fig.axes[ind].lines) > len(segments):
                        #print (f"{__class__.__name__}: Debug: updatePlotLines(): DELETING [{self.__displaySpecs[ind]['yName']}][{yParameter}] one line")
                        self.__fig.axes[ind].lines[0].remove()

                    # Plot each segment separately
                    line = 0
                    for segment in segments:

                        # if this line segment exists, update its data
                        if len(self.__fig.axes[ind].lines) >= line+1:
                            self.__fig.axes[ind].lines[line].set_data(segment.index, segment[yParameter])

                        # otherwise, this is a new line segment to be added
                        else:
                            self.__fig.axes[ind].plot(segment.index, segment[yParameter], color=self.__displaySpecs[ind]['yColor'])

                        # increment line for next loop
                        line += 1

                    # check if we can update the mean and stdev readouts

                    # stats only apply to the first/main subplot dataset
                    if ind == 0:

                        # nothing to do if the label widgets do not exist
                        if self.__meanDisplay is not None and self.__stdDisplay is not None:

                            # we want the appropriate number formatting, but default to 1 decimal if missing
                            decPl = self.__displayDecimals if self.__displayDecimals is not None else 1

                            self.__meanDisplay.config(text=f"{float(round(data[yParameter].mean(),decPl)):.{decPl}f}")
                            self.__stdDisplay.config(text=f"{float(round(data[yParameter].std(),decPl+1)):.{decPl+1}f}")
                            statsUpdated = True

        # reset stats if they weren't updateable this time through
        if 'parent' in self.__statsLoc and not statsUpdated:
            self.__meanDisplay.config(text='--')
            self.__stdDisplay.config(text='--')

    def updatePlot(self):

        # x axis limits
        currentTime = dt.now()
        dayAgo = currentTime + self.__timeRange

        self.updatePlotLines()

        # loop through subplots
        for ind in range(len(self.__displaySpecs)):

            # update the time axes limits
            self.__fig.axes[ind].set_xlim(dayAgo, currentTime)

            # update the vertical axes limits
            self.__fig.axes[ind].relim(visible_only=True)
            self.__fig.axes[ind].autoscale_view(scalex=False,scaley=True)

        self.canvas.draw()
        plt.draw()

    def getSpecs(self, name='generic'):

        # hardcode the appearance of certain parameters
        if name == 'to.raise':
            return {'yName':'Average Setting',
                    'yLabel':'Heat',
                    'yLimit':1.,
                    'color':'red'}
        if name == 'to.lower':
            return {'yName':'Average Setting',
                    'yLabel':'Chill',
                    'yLimit':1.,
                    'color':'blue'}
        if name == 'mfc.air':
            return {'yName':'Average Setting',
                    'yLabel':'Air',
                    'yLimit':5000.,
                    'color':'deepskyblue'}
        if name == 'mfc.co2':
            return {'yName':'Average Setting',
                    #'yLabel':u'CO\u2082',
                    'yLabel':'$CO_2$',
                    'yLimit':20.,
                    'color':'grey'}
        if name == 'mfc.n2':
            return {'yName':'Average Setting',
                    #'yLabel':u'N\u2082',
                    'yLabel':'$N_2$',
                    'yLimit':5000.,
                    'color':'limegreen'}

        # default appearance
        return {'yName':None,
                'yLabel':None,
                'yLimit':None,
                'color':'black'}

def main():

    root = tk.Tk()
    ttk.Label(root,text='Erl2Plot',font='Arial 30 bold').grid(row=0,column=0)

    f = ttk.Frame(root)
    f.grid(row=1,column=0,sticky='nesw')

    plot = Erl2Plot(plotLoc={'parent':f,'row':0,'column':0},
                    displaySpecs=[{'yName':'junk', 'yParameter':'junk'}])

    ttk.Button(f,text='Exit',command=lambda:tk.Tk.quit(root)).grid(row=2,column=0)

    root.mainloop()

if __name__ == "__main__": main()

