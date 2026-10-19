import tkinter as tk
from queue import Queue
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class DataHold:
    def __init__(self):
        self._len = 100
        self.s1cpu = self.fill_queue_zeros()
        self.s1memory = self.fill_queue_zeros()
        self.s1network = self.fill_queue_zeros()
        self.s1swap = self.fill_queue_zeros()
        self.s1disk = self.fill_queue_zeros()
        self.s2cpu = self.fill_queue_zeros()
        self.s2memory = self.fill_queue_zeros()
        self.s2network = self.fill_queue_zeros()
        self.s2swap = self.fill_queue_zeros()
        self.s2disk = self.fill_queue_zeros()
    def fill_queue_zeros(self):    
        for i in range(self._len):
            q = Queue(self._len)
            q.put(0)
        return q

    def update(self, data):

        self.s1cpu = np.roll(self.s1cpu, -data.len)
        self.s1cpu[-1] = data
class GCP_Moniter:
    def __init__(self, root):
        self.data = DataHold()
        self.root = root
        self.root.title("GCP Monitor")
        self.root.geometry("1920x1080")

        # Make the main window rows/columns responsive
        self.root.rowconfigure(2, weight=1)
        self.root.columnconfigure(0, weight=1)

        # --- 1. TOP BUTTON BAR ---
        button_frame = tk.Frame(self.root, bg="#f0f0f0", pady=10)
        button_frame.grid(row=0, column=0, sticky="ew")

        # Configure equal spacing for buttons
        for i in range(4):
            button_frame.columnconfigure(i, weight=1)

        # Control buttons
        btn1 = tk.Button(button_frame, text="Screen 1 (Set A)", command=lambda: self.show_screen(self.screen1))
        btn1.grid(row=0, column=0, padx=5, ipady=5, sticky="ew")

        btn2 = tk.Button(button_frame, text="Screen 2 (Set B)", command=lambda: print("Button 2 clicked"))
        btn2.grid(row=0, column=1, padx=5, ipady=5, sticky="ew")

        btn3 = tk.Button(button_frame, text="Button 3 (Custom Action)", command=lambda: print("Button 3 clicked"))
        btn3.grid(row=0, column=2, padx=5, ipady=5, sticky="ew")

        btn4 = tk.Button(button_frame, text="Button 4 (Custom Action)", command=lambda: print("Button 4 clicked"))
        btn4.grid(row=0, column=3, padx=5, ipady=5, sticky="ew")

        # --- 2. CPU THRESHOLD BAR ---
        threshold_frame = tk.Frame(self.root, bg="#f0f0f0", pady=10)
        threshold_frame.grid(row=1, column=0, sticky="ew")

        threshold_frame.rowconfigure(0, weight=1)
        threshold_frame.rowconfigure(1, weight=1)
        threshold_frame.columnconfigure(0, weight=1)
        threshold_frame.columnconfigure(1, weight=1)
        threshold_frame.columnconfigure(2, weight=1)
        self.cputhreshold = 100.0
        self.memorythreshold = 100.0

        # CPU threshold
        tcpu = tk.Label(threshold_frame, text="CPU Threshold" )
        tcpu.grid(row=0, column=0, sticky="ew")
        self.tcpue = tk.Entry(threshold_frame)
        self.tcpue.grid(row=1, column=0 )
        
        #Memmory threshold
        tmem = tk.Label(threshold_frame, text="Memory Threshold")
        tmem.grid(row=0, column=1, sticky="ew")
        self.tmeme = tk.Entry(threshold_frame)
        self.tmeme.grid(row=1, column=1 )

        #Notifier
        self.tnoti = tk.Label(threshold_frame, text="Status Okay")
        self.tnoti.grid(row=0, column=2, sticky="ew")

        #Set Button
        tbtn = tk.Button(threshold_frame, text="Set", command=lambda: self.setThresholds())
        tbtn.grid(row=1, column=2, padx=5, ipady=5, sticky="nsew")



        # --- 3. SCREEN CONTAINERS ---
        # Both screens occupy the exact same grid cell (row=1, column=0)
        self.screen1 = tk.Frame(self.root)
        self.screen2 = tk.Frame(self.root)

        # Configure 2x2 responsiveness for both screen frames
        for screen in (self.screen1, self.screen2):
            screen.rowconfigure(0, weight=1)
            screen.rowconfigure(1, weight=1)
            screen.columnconfigure(0, weight=1)
            screen.columnconfigure(1, weight=1)
            screen.columnconfigure(2, weight=1)

        # --- 4. POPULATE CHARTS ---
        self.create_screen1_charts()


        # Start by showing Screen 1
        self.show_screen(self.screen1)

    def show_screen(self, screen_to_show):
        """Hides all screens and displays the requested one."""
        self.screen1.grid_forget()
        self.screen2.grid_forget()
        screen_to_show.grid(row=2, column=0, sticky="nsew")

    def embed_chart(self, parent_frame, row, col, plot_func, title):
        """Helper to create a Matplotlib figure and embed it into Tkinter."""
        fig = Figure(figsize=(4, 3), dpi=100)
        ax = fig.add_subplot(111)
        plot_func(ax)
        ax.set_title(title, fontsize=10)
        fig.tight_layout()

        # Link Matplotlib canvas to Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        canvas.draw()

    # --- SCREEN 1 PLOTS (Set A) ---
    def create_screen1_charts(self):
        x = np.linspace(0, 10, 100)
        self.embed_chart(self.screen1, 0, 0, lambda ax: ax.plot(x[:len(self.data.s1cpu.queue)], list(self.data.s1cpu.queue), 'r'), "CPU Usage")
        


    def setThresholds(self):
        self.cputhreshold = self.tcpue.get()
        self.memorythreshold = self.tmeme.get()
        print(self.cputhreshold, self.memorythreshold)
        self.checkThresholds()

    def checkThresholds(self):
        # logic need update
        if True:
            self.tnoti.configure(text="Past CPU Threshold!", bg="red")
        if False:
            self.tnoti.configure(text="Past Memory Threshold!", bg="red")
        elif False:
            self.tnoti.configure(text="Status Okay", bg="#f0f0f0")

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = GCP_Moniter(root)
    root.mainloop()
