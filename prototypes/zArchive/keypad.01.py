#! /usr/bin/python3

## from https://stackoverflow.com/questions/63245400/popup-numpad-numeric-keypad-for-multiple-entry-boxes

import tkinter as tk

class Page(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.create_widgets()

    def create_widgets(self):
        pass

    def show(self):
        self.lift()

class Page1(Page):
    def create_widgets(self):
        self.BackCan = tk.Canvas(self, width=800, height=440, borderwidth=0, bg="white")
        self.BackCan.place(x=0, y=0)
        #Entry Boxes#
        self.Page1e1 = tk.Entry(self, width=12, justify="center")
        self.Page1e1.bind('<FocusIn>', self.master.numpadEntry)
        self.edited = False
        self.Page1e1.place(x=10, y=163, width=102, height=26)
        self.Page1e2 = tk.Entry(self, width=12, justify="center")
        self.Page1e2.bind('<FocusIn>', self.master.numpadEntry)
        self.Page1e2.place(x=129, y=163, width=102, height=26)

class Page2(Page):
    def create_widgets(self):
        #Validation#
        #Page Backround#
        self.BackCan = tk.Canvas(self, width=800, height=440, borderwidth=0, bg="white")
        self.BackCan.place(x=0, y=0)
        ##Entry Boxes##
        self.PrefertHRe = tk.Entry(self, width=12, justify="center")
        self.PrefertHRe.bind('<FocusIn>', self.master.numpadEntry)
        self.edited = False #<-calls numpad
        self.PrefertHRe.place(x=10, y=200, width=102, height=26)
        self.PrefertMINe = tk.Entry(self, width=12, justify="center")
        self.PrefertMINe.place(x=129, y=200, width=102, height=26)
        self.PrefertMINe.bind('<FocusIn>', self.master.numpadEntry)

class NumPad(tk.Toplevel):
    def __init__(self, master=None):
        tk.Toplevel.__init__(self, master)
        self.protocol("WM_DELETE_WINDOW", self.ok)
        self.createWidgets()

    def createWidgets(self):
        btn_list = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '0', 'Close', 'Del']
        r = 1
        c = 0
        n = 0
        
        for label in btn_list:
            cur = tk.Button(self, text=label, width=6, height=3,
                            command=lambda x=label: self.click(x))
            
            cur.grid(row=r, column=c)
            n += 1
            c += 1
            if c == 3:
                c = 0
                r += 1

    def click(self, label):
        if label == 'Del':
            self.master.current_entry.delete(-1)
        elif label == 'Close':
            self.ok()
        else:
            self.master.current_entry.insert('end', label)

    def ok(self):
        self.destroy()
        self.master.focus()
        self.master.numpad = None

class MainView(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)

        self.numpad = None  # NumPad
        self.current_entry = None  # currently selected entry

        p2 = Page2(self)
        p1 = Page1(self)
        Navigation_frame = tk.Frame(self, width=800, height=55, background="bisque")
        container = tk.Frame(self)
        Navigation_frame.pack(side="bottom")
        Navigation_frame.pack_propagate(0)
        container.pack(side="top", fill="both", expand=True)
        NavCan = tk.Canvas(Navigation_frame, width=800, height=55, borderwidth=0, bg="white")
        NavCan.place(x=0, y=0)
        p1.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        p2.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        b1 = tk.Button(Navigation_frame, height=2, width=10, text="1", command=p1.show)
        b2 = tk.Button(Navigation_frame, height=2, width=10, text="2", command=p2.show)
        b1.place(x=144, y=6)
        b2.place(x=253, y=6)

        p1.show()

    def numpadEntry(self, event):
        # change current entry
        self.current_entry = event.widget
        # create numpad if does not exist yet
        if self.numpad is None:
            self.numpad = NumPad(self)
        else:
            self.numpad.lift()


if __name__ == "__main__":
    root = tk.Tk()
    main = MainView(root)
    main.pack(side="top", fill="both", expand=True)
    root.wm_geometry("800x440")
    root.attributes('-fullscreen', False)
    root.mainloop()
