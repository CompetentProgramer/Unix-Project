#!/usr/bin/env python3
"""Serve collected metrics through the team's HTTP API."""

import hmac
import json
import math
import os
import stat
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


FIFO_PATH = "/run/obs-agent/metrics.fifo"
API_KEY = os.environ.get("OBS_API_KEY", "")
HOST = os.environ.get("OBS_BIND", "0.0.0.0")
PORT = int(os.environ.get("AGENT_PORT", "8090"))

# About one hour of samples at a two-second interval.
HISTORY = deque(maxlen=1800)
LOCK = threading.Lock()
LAST_RECEIVED = None

FIELDS = (
    "ts",
    "cpu_percent",
    "mem_percent",
    "disk_io_mbps",
    "net_kbps",
    "load_1m",
)


def prepare_fifo():
    """Create the pipe, refusing to use an ordinary file."""
    try:
        os.mkfifo(FIFO_PATH, 0o660)
    except FileExistsError:
        if not stat.S_ISFIFO(os.lstat(FIFO_PATH).st_mode):
            raise RuntimeError(f"{FIFO_PATH} exists but is not a named pipe")

    os.chmod(FIFO_PATH, 0o660)


def read_samples():
    """Read JSON lines from the collector and retain recent samples."""
    global LAST_RECEIVED

    while True:
        # Opening for reading waits for a collector connection.
        with open(FIFO_PATH, "r", encoding="utf-8") as pipe:
            for line in pipe:
                try:
                    sample = json.loads(line)

                    if not isinstance(sample, dict):
                        continue

                    valid = all(
                        type(sample.get(field)) in (int, float)
                        and math.isfinite(sample[field])
                        for field in FIELDS
                    )
                    if not valid:
                        continue

                    with LOCK:
                        HISTORY.append(sample)
                        LAST_RECEIVED = time.monotonic()

                except (ValueError, TypeError):
                    print("Ignored an invalid collector sample", flush=True)

        # The writer closed its connection; reopen for the next sample.


class Handler(BaseHTTPRequestHandler):
    """Handle dashboard and health-check requests."""

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def send_json(self, code, data):
        body = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)

        if url.path == "/health":
            with LOCK:
                age = (
                    None
                    if LAST_RECEIVED is None
                    else max(0.0, time.monotonic() - LAST_RECEIVED)
                )

            self.send_json(
                200,
                {
                    "status": "ok" if age is not None and age <= 10 else "stale",
                    "age_s": None if age is None else round(age, 2),
                },
            )
            return

        if url.path not in ("/metrics", "/history"):
            self.send_json(404, {"error": "not_found"})
            return

        supplied_key = self.headers.get("X-API-Key", "")
        if not hmac.compare_digest(
            supplied_key.encode("utf-8"), API_KEY.encode("utf-8")
        ):
            self.send_json(401, {"error": "unauthorized"})
            return

        if url.path == "/metrics":
            with LOCK:
                latest = HISTORY[-1] if HISTORY else None

            if latest is None:
                self.send_json(503, {"error": "no_samples_yet"})
            else:
                self.send_json(200, latest)
            return

        query = parse_qs(url.query, keep_blank_values=True)
        try:
            seconds = int(query.get("seconds", ["300"])[0])
            if not 1 <= seconds <= 3600:
                raise ValueError
        except ValueError:
            self.send_json(
                400, {"error": "seconds must be an integer from 1 to 3600"}
            )
            return

        cutoff = time.time() - seconds
        with LOCK:
            recent = [sample for sample in HISTORY if sample["ts"] >= cutoff]

        self.send_json(200, {"samples": recent})


def main():
    if not API_KEY:
        raise SystemExit("OBS_API_KEY must be set before starting the API")

    prepare_fifo()

    with ThreadingHTTPServer((HOST, PORT), Handler) as server:
        threading.Thread(target=read_samples, daemon=True).start()
        print(f"Agent API listening on {HOST}:{PORT}", flush=True)

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
