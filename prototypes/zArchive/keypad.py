#! /usr/bin/python3

## Based on code found online here:
## https://stackoverflow.com/questions/63245400/popup-numpad-numeric-keypad-for-multiple-entry-boxes
## and inspired by an image I found here:
## https://www.jqueryscript.net/other/Visual-Numerical-Keyboard-Easy-Numpad.html

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
        self.BackCan = tk.Canvas(self, width=800, height=440, borderwidth=0, bg='white')
        self.BackCan.place(x=0, y=0)

        #Entry Boxes#
        self.Page1e1 = tk.Entry(self, width=4, font='Arial 20', justify='right', text='24.9')
        self.Page1e1.insert(tk.END, '24.9')
        self.Page1e1.bind('<FocusIn>', self.master.numpadEntry)
        self.Page1e1.place(x=10, y=163, width=102)#, height=26)

        self.Page1e2 = tk.Entry(self, width=4, font='Arial 20', justify='right', text='7.82')
        self.Page1e2.insert(tk.END, '7.82')
        self.Page1e2.bind('<FocusIn>', self.master.numpadEntry)
        self.Page1e2.place(x=129, y=163, width=102)#, height=26)

        self.edited = False

class Page2(Page):
    def create_widgets(self):
        #Validation#
        #Page Backround#
        self.BackCan = tk.Canvas(self, width=800, height=440, borderwidth=0, bg='white')
        self.BackCan.place(x=0, y=0)
        ##Entry Boxes##
        self.PrefertHRe = tk.Entry(self, width=12, justify='center')
        self.PrefertHRe.bind('<FocusIn>', self.master.numpadEntry)
        self.edited = False #<-calls numpad
        self.PrefertHRe.place(x=10, y=200, width=102, height=26)
        self.PrefertMINe = tk.Entry(self, width=12, justify='center')
        self.PrefertMINe.place(x=129, y=200, width=102, height=26)
        self.PrefertMINe.bind('<FocusIn>', self.master.numpadEntry)

class NumPad(tk.Toplevel):
    btn_list = ['7', '8', '9', 'Del', '4', '5', '6', 'Clear', '1', '2', '3', 'Cancel', '0', 'Dot', 'Done']
    key_images = []

    def __init__(self, master=None):
        tk.Toplevel.__init__(self, master)
        #print (f"root width is {root.winfo_width()}, height is {root.winfo_height()}")
        #print (f"popup width is {self.winfo_width()}, height is {self.winfo_height()}")
        # kludge? assuming popup is 200x200
        self.geometry(f"+{int((root.winfo_width()-200)/2)}+{int((root.winfo_height()-200)/2)}")
        self.protocol('WM_DELETE_WINDOW', self.ok)
        self.overrideredirect(1)
        self.display = tk.Entry(self,
            #text=self.master.current_entry.get(),
            #width=self.master.current_entry['width'],
            width=12,
            font='Arial 24', justify='right')
        self.display.grid(row=1,column=1,columnspan=4,padx=10,pady=10)
        self.loadImages()
        self.createWidgets()
        #self.value=value

    def loadImages(self):
        if len(NumPad.key_images) == 0:
             for label in NumPad.btn_list:
                 NumPad.key_images.append(tk.PhotoImage(file='/home/ocedadmin/Desktop/img/key' + label + '.png'))

    def createWidgets(self):
        # when first opening, copy the initial value from the field being edited
        self.display.delete(0,'end')
        self.display.insert(0,self.master.current_entry.get())

        #btn_list = ['7', '8', '9', 'Del', '4', '5', '6', 'Clear', '1', '2', '3', 'Cancel', '0', 'Dot', 'Done']
        r = 2
        c = 1
        n = 0
        
        for label in NumPad.btn_list:

            # some buttons are sized differently
            if label == '0':
                #w = 15
                sp = 2
            elif label in ['Del', 'Clear', 'Cancel', 'Done']:
                #w = 10
                sp = 1
            else:
                #w = 6
                sp = 1

            cur = tk.Button(self, #text=label,
                image=NumPad.key_images[n],
                #width=w, height=3,
                font='Arial 16 bold',
                command=lambda x=label: self.click(x))
            
            cur.grid(row=r, column=c, columnspan=sp)
            n += 1
            c += sp
            if c >= 5:
                c = 1
                r += 1

    def click(self, label):
        if label == 'Del':
            #self.master.current_entry.delete(-1)
            self.display.delete(self.display.index('end')-1)
        elif label == 'Clear':
            self.display.delete(0,'end')
        elif label == 'Cancel':
            self.ok()
        elif label == 'Done':
            self.master.current_entry.delete(0,'end')
            self.master.current_entry.insert(0,self.display.get())
            self.ok()
        elif label == 'Dot':
            # numbers cannot have more than one decimal point
            if '.' not in self.display.get():
                self.display.insert('end', '.')
        else:
            #self.master.current_entry.insert('end', label)
            self.display.insert('end', label)

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
        Navigation_frame = tk.Frame(self, width=800, height=55, background='bisque')
        container = tk.Frame(self)
        Navigation_frame.pack(side='bottom')
        Navigation_frame.pack_propagate(0)
        container.pack(side='top', fill='both', expand=True)
        NavCan = tk.Canvas(Navigation_frame, width=800, height=55, borderwidth=0, bg='white')
        NavCan.place(x=0, y=0)
        p1.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        p2.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
        b1 = tk.Button(Navigation_frame, height=2, width=10, text='1', command=p1.show)
        b2 = tk.Button(Navigation_frame, height=2, width=10, text='2', command=p2.show)
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


if __name__ == '__main__':
    root = tk.Tk()
    main = MainView(root)
    main.pack(side='top', fill='both', expand=True)
    root.wm_geometry('800x440')
    root.attributes('-fullscreen', False)
    root.mainloop()
