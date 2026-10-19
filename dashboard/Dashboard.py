import tkinter as tk
from collections import deque
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import APICaller

class DataHold:
    def __init__(self):
        self._len = 100
        self.s1cpu =        deque([0]*self._len, maxlen=self._len)
        self.s1memory =     deque([0]*self._len, maxlen=self._len)
        self.s1network =    deque([0]*self._len, maxlen=self._len)
        self.s1load =       deque([0]*self._len, maxlen=self._len)
        self.s1disk =       deque([0]*self._len, maxlen=self._len)
        self.s2cpu =        deque([0]*self._len, maxlen=self._len)
        self.s2memory =     deque([0]*self._len, maxlen=self._len)
        self.s2network =    deque([0]*self._len, maxlen=self._len)
        self.s2load =       deque([0]*self._len, maxlen=self._len)
        self.s2disk =       deque([0]*self._len, maxlen=self._len)
        self.s3cpu =        deque([0]*self._len, maxlen=self._len)
        self.s3memory =     deque([0]*self._len, maxlen=self._len)
        self.s3network =    deque([0]*self._len, maxlen=self._len)
        self.s3load =       deque([0]*self._len, maxlen=self._len)
        self.s3disk =       deque([0]*self._len, maxlen=self._len)
        self.s4cpu =        deque([0]*self._len, maxlen=self._len)
        self.s4memory =     deque([0]*self._len, maxlen=self._len)
        self.s4network =    deque([0]*self._len, maxlen=self._len)
        self.s4load =       deque([0]*self._len, maxlen=self._len)
        self.s4disk =       deque([0]*self._len, maxlen=self._len)


    def update1(self):
        temp = APICaller.pollerFunc(1)
        self.s1cpu.append(temp["cpu_percent"])
        self.s1memory.append(temp["mem_percent"])
        self.s1disk.append(temp["disk_io_mbps"])
        self.s1network.append(temp["net_kbps"])
        self.s1load.append(temp["load_1m"])

    def update2(self):
        temp = APICaller.pollerFunc(2)
        self.s2cpu.append(temp["cpu_percent"])
        self.s2memory.append(temp["mem_percent"])
        self.s2disk.append(temp["disk_io_mbps"])
        self.s2network.append(temp["net_kbps"])
        self.s2load.append(temp["load_1m"])

    def update3(self):
        temp = APICaller.pollerFunc(3)
        self.s3cpu.append(temp["cpu_percent"])
        self.s3memory.append(temp["mem_percent"])
        self.s3disk.append(temp["disk_io_mbps"])
        self.s3network.append(temp["net_kbps"])
        self.s3load.append(temp["load_1m"])

    def update4(self):
        temp = APICaller.pollerFunc(4)
        self.s4cpu.append(temp["cpu_percent"])
        self.s4memory.append(temp["mem_percent"])
        self.s4disk.append(temp["disk_io_mbps"])
        self.s4network.append(temp["net_kbps"])
        self.s4load.append(temp["load_1m"])
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
        btn1 = tk.Button(button_frame, text="Server 1", command=lambda: self.show_screen(self.screen1))
        btn1.grid(row=0, column=0, padx=5, ipady=5, sticky="ew")

        btn2 = tk.Button(button_frame, text="Server 2", command=lambda: self.show_screen(self.screen2))
        btn2.grid(row=0, column=1, padx=5, ipady=5, sticky="ew")

        btn3 = tk.Button(button_frame, text="Server 3", command=lambda: self.show_screen(self.screen3))
        btn3.grid(row=0, column=2, padx=5, ipady=5, sticky="ew")

        btn4 = tk.Button(button_frame, text="Server 4", command=lambda: self.show_screen(self.screen4))
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
        self.screen1 = tk.Frame(self.root)
        self.screen2 = tk.Frame(self.root)
        self.screen3 = tk.Frame(self.root)
        self.screen4 = tk.Frame(self.root)

        # Configure 2x2 responsiveness for both screen frames
        for screen in (self.screen1, self.screen2, self.screen3, self.screen4):
            screen.rowconfigure(0, weight=1)
            screen.rowconfigure(1, weight=1)
            screen.columnconfigure(0, weight=1)
            screen.columnconfigure(1, weight=1)
            screen.columnconfigure(2, weight=1)

        # --- 4. INNIT CHARTS ---
        # creates references for update proccess to work correctly
        self.x = np.linspace(0, 10, 100)
        self.create_screen1_charts()
        self.create_screen2_charts()
        self.create_screen3_charts()
        self.create_screen4_charts()
        self.show_screen(self.screen1)


    def show_screen(self, screen_to_show):
        """Hides all screens and displays the requested one."""
        self.screen1.grid_forget()
        self.screen2.grid_forget()
        self.screen3.grid_forget()
        self.screen4.grid_forget()
        screen_to_show.grid(row=2, column=0, sticky="nsew")

    def embed_chart(self, parent_frame, row, col, plot_func, title):
        """Helper to create a Matplotlib figure and embed it into Tkinter."""
        fig = Figure(figsize=(4, 3), dpi=100)
        ax = fig.add_subplot(111)

        # Capture whatever the plot function returns
        # (Since your lambdas evaluate tuples, this captures the tuple)
        plot_func(ax)

        line = ax.get_lines()[0]
        ax.set_title(title, fontsize=10)
        ax.set_xticklabels([])
        fig.tight_layout()

        # Link Matplotlib canvas to Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        canvas.draw()

        return line, canvas

    # --- SCREEN 1 PLOTS (Set A) ---
    def create_screen1_charts(self):
        self.mon1cpu = self.embed_chart(self.screen1, 0, 0,
                         lambda ax: (ax.plot(self.x[:len(self.data.s1cpu)], list(self.data.s1cpu), 'r'),
                                     ax.set_ylim(0, 100)), "CPU Usage")
        self.mon1mem = self.embed_chart(self.screen1, 0, 1,
                         lambda ax: (ax.plot(self.x[:len(self.data.s1memory)], list(self.data.s1memory), 'r'),
                                     ax.set_ylim(0, 100)), "Memory Usage")
        self.mon1disk = self.embed_chart(self.screen1, 0, 2,
                         lambda ax: (ax.plot(self.x[:len(self.data.s1disk)], list(self.data.s1disk), 'r'),
                                     ax.set_ylim(0, 120)), "Disk IO Mbps")
        self.mon1net = self.embed_chart(self.screen1, 1, 0,
                         lambda ax: (ax.plot(self.x[:len(self.data.s1network)], list(self.data.s1network), 'r'),
                                     ax.set_ylim(0, 3.5)), "Network Usage Kbps")
        self.mon1load =self.embed_chart(self.screen1, 1, 1,
                         lambda ax: (ax.plot(self.x[:len(self.data.s1load)], list(self.data.s1load), 'r'),
                                     ax.set_ylim(0, 5)), "Load 1m")
    def create_screen2_charts(self):
        self.mon2cpu = self.embed_chart(self.screen2, 0, 0,
                         lambda ax: (ax.plot(self.x[:len(self.data.s2cpu)], list(self.data.s2cpu), 'r'),
                                     ax.set_ylim(0, 100)), "CPU Usage (S2)")
        self.mon2mem = self.embed_chart(self.screen2, 0, 1,
                         lambda ax: (ax.plot(self.x[:len(self.data.s2memory)], list(self.data.s2memory), 'r'),
                                     ax.set_ylim(0, 100)), "Memory Usage (S2)")
        self.mon2disk = self.embed_chart(self.screen2, 0, 2,
                         lambda ax: (ax.plot(self.x[:len(self.data.s2disk)], list(self.data.s2disk), 'r'),
                                     ax.set_ylim(0, 120)), "Disk IO Mbps (S2)")
        self.mon2net = self.embed_chart(self.screen2, 1, 0,
                         lambda ax: (ax.plot(self.x[:len(self.data.s2network)], list(self.data.s2network), 'r'),
                                     ax.set_ylim(0, 3.5)), "Network Usage Kbps (S2)")
        self.mon2load =self.embed_chart(self.screen2, 1, 1,
                         lambda ax: (ax.plot(self.x[:len(self.data.s2load)], list(self.data.s2load), 'r'),
                                     ax.set_ylim(0, 5)), "Load 1m (S2)")
    def create_screen3_charts(self):
        self.mon3cpu = self.embed_chart(self.screen3, 0, 0,
                                        lambda ax: (
                                            ax.plot(self.x[:len(self.data.s3cpu)], list(self.data.s3cpu),'r'),
                                            ax.set_ylim(0, 100)), "CPU Usage (S3)")
        self.mon3mem = self.embed_chart(self.screen3, 0, 1,
                                        lambda ax: (
                                            ax.plot(self.x[:len(self.data.s3memory)], list(self.data.s3memory),'r'),
                                            ax.set_ylim(0, 100)), "Memory Usage (S3)")
        self.mon3disk = self.embed_chart(self.screen3, 0, 2,
                                         lambda ax: (
                                             ax.plot(self.x[:len(self.data.s3disk)], list(self.data.s3disk),'r'),
                                             ax.set_ylim(0, 120)), "Disk IO Mbps (S3)")
        self.mon3net = self.embed_chart(self.screen3, 1, 0,
                                        lambda ax: (ax.plot(self.x[:len(self.data.s3network)],
                                                            list(self.data.s3network), 'r'),
                                                    ax.set_ylim(0, 3.5)), "Network Usage Kbps (S3)")
        self.mon3load = self.embed_chart(self.screen3, 1, 1,
                                         lambda ax: (
                                             ax.plot(self.x[:len(self.data.s3load)], list(self.data.s3load),'r'),
                                             ax.set_ylim(0, 5)), "Load 1m (S3)")
    def create_screen4_charts(self):
        self.mon4cpu = self.embed_chart(self.screen4, 0, 0,
                         lambda ax: (ax.plot(self.x[:len(self.data.s4cpu)], list(self.data.s4cpu), 'r'),
                                     ax.set_ylim(0, 100)), "CPU Usage (S4)")
        self.mon4mem = self.embed_chart(self.screen4, 0, 1,
                         lambda ax: (ax.plot(self.x[:len(self.data.s4memory)], list(self.data.s4memory), 'r'),
                                     ax.set_ylim(0, 100)), "Memory Usage (S4)")
        self.mon4disk = self.embed_chart(self.screen4, 0, 2,
                         lambda ax: (ax.plot(self.x[:len(self.data.s4disk)], list(self.data.s4disk), 'r'),
                                     ax.set_ylim(0, 120)), "Disk IO Mbps (S4)")
        self.mon4net = self.embed_chart(self.screen4, 1, 0,
                         lambda ax: (ax.plot(self.x[:len(self.data.s4network)], list(self.data.s4network), 'r'),
                                     ax.set_ylim(0, 3.5)), "Network Usage Kbps (S4)")
        self.mon4load =self.embed_chart(self.screen4, 1, 1,
                         lambda ax: (ax.plot(self.x[:len(self.data.s4load)], list(self.data.s4load), 'r'),
                                     ax.set_ylim(0, 5)), "Load 1m (S4)")

    def _update_screen_canvas(self, mappings):
        """Helper to run vector updates over structured visual charts."""
        for (line, canvas), data_deque in mappings:
            y_data = list(data_deque)
            if not y_data:
                continue
            x_data = self.x[:len(y_data)]
            line.set_data(x_data, y_data)
            ax = line.axes
            ax.relim()
            ax.autoscale_view(scaley=False)
            canvas.draw_idle()

    def update_charts1(self):
        self.data.update1()
        # Mapping of chart tuples (line, canvas) to their data queues
        mappings = [
            (self.mon1cpu, self.data.s1cpu),
            (self.mon1mem, self.data.s1memory),
            (self.mon1disk, self.data.s1disk),
            (self.mon1net, self.data.s1network),
            (self.mon1load, self.data.s1load)
        ]
        self._update_screen_canvas(mappings)
    def update_charts2(self):
        self.data.update2()
        # Mapping of chart tuples (line, canvas) to their data queues
        mappings = [
            (self.mon2cpu, self.data.s2cpu),
            (self.mon2mem, self.data.s2memory),
            (self.mon2disk, self.data.s2disk),
            (self.mon2net, self.data.s2network),
            (self.mon2load, self.data.s2load)
        ]
        self._update_screen_canvas(mappings)
    def update_charts3(self):
        self.data.update3()
        # Mapping of chart tuples (line, canvas) to their data queues
        mappings = [
            (self.mon3cpu, self.data.s3cpu),
            (self.mon3mem, self.data.s3memory),
            (self.mon3disk, self.data.s3disk),
            (self.mon3net, self.data.s3network),
            (self.mon3load, self.data.s3load)
        ]
        self._update_screen_canvas(mappings)
    def update_charts4(self):
        self.data.update4()
        # Mapping of chart tuples (line, canvas) to their data queues
        mappings = [
            (self.mon4cpu, self.data.s4cpu),
            (self.mon4mem, self.data.s4memory),
            (self.mon4disk, self.data.s4disk),
            (self.mon4net, self.data.s4network),
            (self.mon4load, self.data.s4load)
        ]
        self._update_screen_canvas(mappings)

    def setThresholds(self):
        self.cputhreshold = float(self.tcpue.get())
        self.memorythreshold = float(self.tmeme.get())
        print(self.cputhreshold, self.memorythreshold)
        self.checkThresholds()

    def checkThresholds(self):
        # logic need update
        if self.cputhreshold < self.data.s1cpu[99] or self.cputhreshold < self.data.s2cpu[99] or self.cputhreshold < self.data.s3cpu[99] or self.cputhreshold < self.data.s4cpu[99]:
            self.tnoti.configure(text="Past CPU Threshold!", bg="red")
        elif self.memorythreshold < self.data.s1memory[99] or self.memorythreshold < self.data.s2memory[99] or self.memorythreshold < self.data.s3memory[99] or self.memorythreshold < self.data.s4memory[99]:
            self.tnoti.configure(text="Past Memory Threshold!", bg="red")
        else:
            self.tnoti.configure(text="Status Okay", bg="#f0f0f0")

    def UpdateProcess(self):
        self.update_charts1()
        self.update_charts2()
        self.update_charts3()
        self.update_charts4()
        self.checkThresholds()

        self.root.after(1000, self.UpdateProcess)

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = GCP_Moniter(root)
    app.UpdateProcess()
    root.mainloop()


