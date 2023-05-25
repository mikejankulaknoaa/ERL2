#! /usr/bin/python

# Fullscreen with no menu bar at top (which is what I want)

# see https://www.geeksforgeeks.org/how-to-create-full-screen-window-in-tkinter/

# importing tkinter for gui
import tkinter as tk
 
# creating window
window = tk.Tk()
 
# setting attribute
window.attributes('-fullscreen', True)
window.title("Geeks For Geeks")
 
# creating text label to display on window screen
label = tk.Label(window, text="Hello Tkinter!")
label.pack()
 
window.mainloop()
