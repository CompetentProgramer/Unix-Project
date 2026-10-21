"""GCP monitor: live and historical charts for the observability agents.

Run:  python Dashboard.py      (needs servers.yaml next to this file; copy servers_example.yaml)

How it works
  * One background thread per server polls its agent every 2 seconds, so a dead
    or blocked server can never freeze the window or stop the other servers.
  * Every sample is also saved to history.db (SQLite), so history survives a
    restart. When a server comes back after an outage, the gap is refilled from
    the agent's own one-hour buffer.
  * The window only draws; it reads what the threads collected.
Collection starts as soon as the app starts.
"""

import json
import sqlite3
import threading
import time
import tkinter as tk
from bisect import bisect_left
from pathlib import Path
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import APICaller

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "history.db"
THRESHOLD_PATH = HERE / "thresholds.json"

POLL_SECONDS = 2        # the agent produces a sample every 2 seconds
REFRESH_MS = 1000       # how often the window redraws
KEEP_SECONDS = 6 * 3600 # history kept in memory and in the database
DOWN_AFTER = 6          # no reply for this long -> DOWN
STALE_AFTER = 10        # replies but no new sample for this long -> STALE
GAP_SECONDS = 10        # break the chart line where samples are missing
MAX_POINTS = 1500       # draw at most this many points per chart

# key must match the agent's field names (docs/INTERFACES.md)
METRICS = (
    {"key": "cpu_percent", "title": "CPU usage (%)", "short": "CPU %", "fixed": 100.0},
    {"key": "mem_percent", "title": "Memory usage (%)", "short": "Memory %", "fixed": 100.0},
    {"key": "disk_io_mbps", "title": "Disk I/O (MB/s)", "short": "Disk MB/s", "fixed": None},
    {"key": "net_kbps", "title": "Network (KB/s)", "short": "Net KB/s", "fixed": None},
    {"key": "load_1m", "title": "Load average (1 min)", "short": "Load", "fixed": None},
)
KEYS = [metric["key"] for metric in METRICS]

WINDOWS = {
    "Last 2 minutes": 120,
    "Last 10 minutes": 600,
    "Last hour": 3600,
    "Last 6 hours": 6 * 3600,
}

STATUS_COLORS = {
    "OK": "#c8e6c9",
    "STALE": "#ffe0b2",
    "DOWN": "#ffcdd2",
    "WAITING": "#f0f0f0",
}
BAR_BG = "#f0f0f0"


def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as db:
        columns = ", ".join(f"{key} REAL" for key in KEYS)
        db.execute(
            f"CREATE TABLE IF NOT EXISTS samples "
            f"(server TEXT, ts REAL, {columns}, PRIMARY KEY (server, ts))"
        )
        db.execute("DELETE FROM samples WHERE ts < ?", (time.time() - KEEP_SECONDS,))
    # the 'with' block commits but does not close
    db.close()


class ServerState:
    """Everything the dashboard knows about one server. Thread-safe."""

    def __init__(self, server):
        self.server = server
        self.name = server["name"]
        self.lock = threading.Lock()
        self.ts = []                          # sample times, oldest first
        self.cols = {key: [] for key in KEYS}
        self.started = time.monotonic()
        self.last_ok = 0.0                    # last good reply
        self.last_new = 0.0                   # last reply with a new sample
        self.error = "starting"

    # ---- data -----------------------------------------------------------
    def add(self, samples, fresh=True):
        """Append samples newer than what we have. Returns the ones added."""
        added = []
        with self.lock:
            last = self.ts[-1] if self.ts else 0.0
            for sample in sorted(samples, key=lambda s: s["ts"]):
                if sample["ts"] > last:
                    self.ts.append(sample["ts"])
                    for key in KEYS:
                        self.cols[key].append(sample[key])
                    last = sample["ts"]
                    added.append(sample)
            if added and fresh:
                self.last_new = time.monotonic()
            cutoff = time.time() - KEEP_SECONDS
            if self.ts and self.ts[0] < cutoff:
                drop = bisect_left(self.ts, cutoff)
                del self.ts[:drop]
                for key in KEYS:
                    del self.cols[key][:drop]
        return added

    def latest(self):
        with self.lock:
            if not self.ts:
                return None
            return {key: self.cols[key][-1] for key in KEYS}

    def window(self, seconds):
        """(times, {key: values}) for the last `seconds`, gaps marked with NaN."""
        cutoff = time.time() - seconds
        with self.lock:
            start = bisect_left(self.ts, cutoff)
            ts = np.array(self.ts[start:], dtype=float)
            cols = {key: np.array(self.cols[key][start:], dtype=float) for key in KEYS}
        if ts.size == 0:
            return ts, cols

        step = max(1, ts.size // MAX_POINTS)
        ts = ts[::step]
        cols = {key: values[::step] for key, values in cols.items()}

        # lift the pen where the agent was down instead of drawing a false line
        breaks = np.where(np.diff(ts) > max(GAP_SECONDS, 6 * step))[0] + 1
        if breaks.size:
            ts = np.insert(ts, breaks, ts[breaks - 1] + 1.0)
            cols = {key: np.insert(values, breaks, np.nan) for key, values in cols.items()}
        return ts, cols

    def status(self):
        now = time.monotonic()
        if now - (self.last_ok or self.started) > DOWN_AFTER:
            return "DOWN"
        if not self.last_ok:
            return "WAITING"
        if now - self.last_new > STALE_AFTER:
            return "STALE"
        return "OK"

    # ---- background thread ---------------------------------------------
    def save(self, db, rows):
        if not rows:
            return
        try:
            db.executemany(
                f"INSERT OR IGNORE INTO samples VALUES (?, ?, {', '.join('?' * len(KEYS))})",
                [(self.name, row["ts"], *[row[key] for key in KEYS]) for row in rows],
            )
            db.commit()
        except sqlite3.Error as exc:
            print(f"{self.name}: could not save history ({exc})", flush=True)

    def load_saved(self, db):
        try:
            rows = db.execute(
                f"SELECT ts, {', '.join(KEYS)} FROM samples "
                "WHERE server = ? AND ts > ? ORDER BY ts",
                (self.name, time.time() - KEEP_SECONDS),
            ).fetchall()
        except sqlite3.Error as exc:
            print(f"{self.name}: could not read history ({exc})", flush=True)
            return
        self.add(
            [dict(zip(("ts", *KEYS), row)) for row in rows],
            fresh=False,
        )

    def run(self, stop):
        """Poll forever. Never raises; errors only change self.error."""
        db = sqlite3.connect(DB_PATH, timeout=10)
        self.load_saved(db)
        was_down = True

        while not stop.is_set():
            sample, error = APICaller.fetch_latest(self.server)
            if sample is None:
                self.error = error
                was_down = True
            else:
                self.last_ok = time.monotonic()
                self.error = ""
                if was_down:
                    # first contact or back from an outage: refill from the agent
                    history, _ = APICaller.fetch_history(self.server, 3600)
                    if history:
                        self.save(db, self.add(history))
                    was_down = False
                self.save(db, self.add([sample]))
            stop.wait(POLL_SECONDS)

        db.close()


class MetricChart:
    """One matplotlib chart inside a Tk frame."""

    def __init__(self, parent, row, col, metric, server_name):
        self.metric = metric
        figure = Figure(figsize=(4, 3), dpi=100)
        self.ax = figure.add_subplot(111)
        (self.line,) = self.ax.plot([], [], color="tab:blue", linewidth=1.3)
        self.limit_line = self.ax.axhline(
            0, color="red", linestyle="--", linewidth=1, visible=False
        )
        self.ax.set_title(f"{metric['title']}  {server_name}", fontsize=10)
        self.ax.set_xlabel("minutes ago", fontsize=8)
        self.ax.tick_params(labelsize=8)
        self.ax.grid(alpha=0.3)
        figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(figure, master=parent)
        self.canvas.get_tk_widget().grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

    def update(self, ts, values, window_seconds, limit):
        self.line.set_data((ts - time.time()) / 60.0, values)
        self.ax.set_xlim(-window_seconds / 60.0, 0)

        finite = values[np.isfinite(values)]
        if self.metric["fixed"]:
            top = self.metric["fixed"]
        else:
            peak = float(finite.max()) if finite.size else 0.0
            top = max(peak * 1.15, 1.0)
            if limit is not None:
                top = max(top, limit * 1.1)
        self.ax.set_ylim(0, top)

        if limit is None:
            self.limit_line.set_visible(False)
        else:
            self.limit_line.set_ydata([limit, limit])
            self.limit_line.set_visible(True)
        self.canvas.draw_idle()


def load_thresholds():
    try:
        raw = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        key: float(raw[key])
        for key in KEYS
        if isinstance(raw.get(key), (int, float))
    }


def save_thresholds(thresholds):
    try:
        THRESHOLD_PATH.write_text(json.dumps(thresholds), encoding="utf-8")
    except OSError as exc:
        print(f"could not save thresholds ({exc})", flush=True)


class Monitor:
    """The window."""

    def __init__(self, root, states):
        self.root = root
        self.states = states
        self.thresholds = load_thresholds()
        self.window_seconds = WINDOWS["Last 2 minutes"]
        self.current = 0

        root.title("GCP Monitor")
        root.geometry("1500x900")
        root.rowconfigure(2, weight=1)
        root.columnconfigure(0, weight=1)

        # --- server buttons + time window ---
        top = tk.Frame(root, bg=BAR_BG, pady=10)
        top.grid(row=0, column=0, sticky="ew")
        for i in range(len(states)):
            top.columnconfigure(i, weight=1)
        self.buttons = []
        for i, state in enumerate(states):
            button = tk.Button(top, text=state.name, command=lambda i=i: self.show_screen(i))
            button.grid(row=0, column=i, padx=5, ipady=5, sticky="ew")
            self.buttons.append(button)
        picker = tk.Frame(top, bg=BAR_BG)
        picker.grid(row=1, column=0, columnspan=len(states), pady=(8, 0))
        tk.Label(picker, text="Time window:", bg=BAR_BG).pack(side="left", padx=5)
        self.window_box = ttk.Combobox(
            picker, state="readonly", values=list(WINDOWS), width=18
        )
        self.window_box.set("Last 2 minutes")
        self.window_box.bind("<<ComboboxSelected>>", self.on_window_change)
        self.window_box.pack(side="left")

        # --- thresholds + alert ---
        bar = tk.Frame(root, bg=BAR_BG, pady=10)
        bar.grid(row=1, column=0, sticky="ew")
        self.entries = {}
        for column, metric in enumerate(METRICS):
            bar.columnconfigure(column, weight=1)
            tk.Label(bar, text=f"{metric['short']} threshold", bg=BAR_BG).grid(row=0, column=column)
            entry = tk.Entry(bar, width=10)
            current = self.thresholds.get(metric["key"])
            entry.insert(0, "" if current is None else f"{current:g}")
            entry.grid(row=1, column=column)
            self.entries[metric["key"]] = entry
        bar.columnconfigure(len(METRICS), weight=2)
        tk.Button(bar, text="Set thresholds", command=self.set_thresholds).grid(
            row=0, column=len(METRICS), rowspan=2, padx=5, ipady=5
        )
        self.alert = tk.Label(
            bar, text="Status OK", bg=BAR_BG, font=("TkDefaultFont", 11, "bold")
        )
        self.alert.grid(row=2, column=0, columnspan=len(METRICS) + 1, pady=(8, 0))
        tk.Label(
            bar, text="Leave a box empty for no limit. Limits are saved and shown as red dashed lines.",
            bg=BAR_BG, fg="gray30",
        ).grid(row=3, column=0, columnspan=len(METRICS) + 1)

        # --- one screen of charts per server ---
        self.screens, self.charts = [], []
        for state in states:
            frame = tk.Frame(root)
            for column in range(3):
                frame.columnconfigure(column, weight=1)
            for row in range(2):
                frame.rowconfigure(row, weight=1)
            self.charts.append(
                [
                    MetricChart(frame, n // 3, n % 3, metric, state.name)
                    for n, metric in enumerate(METRICS)
                ]
            )
            self.screens.append(frame)

        # --- status bar ---
        self.status_bar = tk.Label(root, text="", anchor="w", bg=BAR_BG, fg="gray30")
        self.status_bar.grid(row=3, column=0, sticky="ew")

        self.show_screen(0)
        self.refresh()

    # ---- user actions ---------------------------------------------------
    def show_screen(self, index):
        for screen in self.screens:
            screen.grid_forget()
        self.current = index
        self.screens[index].grid(row=2, column=0, sticky="nsew")
        self.draw_current()

    def on_window_change(self, _event=None):
        self.window_seconds = WINDOWS[self.window_box.get()]
        self.draw_current()

    def set_thresholds(self):
        new = {}
        for metric in METRICS:
            text = self.entries[metric["key"]].get().strip()
            if not text:
                continue
            try:
                value = float(text)
                if value < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Threshold",
                    f"{metric['short']}: '{text}' is not a number of 0 or more.",
                )
                return
            new[metric["key"]] = value
        self.thresholds = new
        save_thresholds(new)
        self.refresh_alerts()
        self.draw_current()

    # ---- drawing --------------------------------------------------------
    def draw_current(self):
        state = self.states[self.current]
        ts, cols = state.window(self.window_seconds)
        for chart in self.charts[self.current]:
            key = chart.metric["key"]
            chart.update(ts, cols[key], self.window_seconds, self.thresholds.get(key))

    def refresh_alerts(self):
        problems = []
        for state, button in zip(self.states, self.buttons):
            status = state.status()
            button.configure(text=f"{state.name}  [{status}]", bg=STATUS_COLORS[status])
            if status == "DOWN":
                problems.append(f"{state.name} is DOWN")
            elif status == "OK":
                latest = state.latest()
                for metric in METRICS:
                    limit = self.thresholds.get(metric["key"])
                    value = latest[metric["key"]] if latest else None
                    if limit is not None and value is not None and value > limit:
                        problems.append(
                            f"{state.name} {metric['short']} {value:.1f} > {limit:g}"
                        )

        if problems:
            shown = "; ".join(problems[:3])
            extra = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
            self.alert.configure(text=f"ALERT: {shown}{extra}", bg="red", fg="white")
        else:
            self.alert.configure(text="Status OK", bg=BAR_BG, fg="black")

        errors = [f"{s.name}: {s.error}" for s in self.states if s.error]
        self.status_bar.configure(text="  |  ".join(errors) or "All servers answering")

    def refresh(self):
        try:
            self.refresh_alerts()
            self.draw_current()
        except Exception as exc:  # the loop must never die
            self.status_bar.configure(text=f"display error: {exc}")
        finally:
            self.root.after(REFRESH_MS, self.refresh)


def main():
    try:
        servers = APICaller.load_servers()
    except APICaller.ConfigError as exc:
        raise SystemExit(f"error: {exc}")

    init_db()
    states = [ServerState(server) for server in servers]
    stop = threading.Event()
    for state in states:
        threading.Thread(target=state.run, args=(stop,), daemon=True).start()

    root = tk.Tk()
    Monitor(root, states)

    def close():
        stop.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()


if __name__ == "__main__":
    main()
