#! /usr/bin/python

# This is fullscreen but still shows PI menu bar and an individual Tk menu bar
# (which is not generally what I want)

# see https://www.geeksforgeeks.org/how-to-create-full-screen-window-in-tkinter/

# importing tkinter gui
import tkinter as tk
 
#creating window
window=tk.Tk()
 
#getting screen width and height of display
width= window.winfo_screenwidth()
height= window.winfo_screenheight()
#setting tkinter window size
window.geometry("%dx%d" % (width, height))
window.title("Geeeks For Geeks")
label = tk.Label(window, text="Hello Tkinter!")
label.pack()
 
window.mainloop()
