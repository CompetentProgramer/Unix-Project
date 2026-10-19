#!/usr/bin/env python3
"""Collect server metrics and send JSON samples through a named pipe."""

import argparse
import errno
import json
import os
import time

import psutil


FIFO_PATH = "/run/obs-agent/metrics.fifo"
SAMPLE_INTERVAL = 2.0


def byte_totals():
    """Read cumulative disk and network byte counters."""
    disk = psutil.disk_io_counters()
    network = psutil.net_io_counters()

    disk_bytes = disk.read_bytes + disk.write_bytes if disk else 0
    network_bytes = network.bytes_sent + network.bytes_recv

    return disk_bytes, network_bytes


def samples():
    """Generate a new measurement approximately every two seconds."""
    previous_disk, previous_network = byte_totals()
    previous_time = time.monotonic()

    # Prime CPU measurement so the first reported interval is meaningful.
    psutil.cpu_percent(interval=None)

    while True:
        time.sleep(SAMPLE_INTERVAL)

        disk_bytes, network_bytes = byte_totals()
        current_time = time.monotonic()
        elapsed = current_time - previous_time

        sample = {
            "ts": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "mem_percent": psutil.virtual_memory().percent,
            "disk_io_mbps": round(
                max(0, disk_bytes - previous_disk) / elapsed / 1_000_000,
                4,
            ),
            "net_kbps": round(
                max(0, network_bytes - previous_network) / elapsed / 1_000,
                4,
            ),
            "load_1m": round(os.getloadavg()[0], 4),
        }

        previous_disk = disk_bytes
        previous_network = network_bytes
        previous_time = current_time

        yield sample


def write_to_fifo(sample):
    """Drop a sample if the reader is absent or the pipe is full."""
    payload = (json.dumps(sample) + "\n").encode("utf-8")

    try:
        fd = os.open(FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno in (errno.ENXIO, errno.ENOENT):
            return
        raise

    try:
        # Each small sample is written as one complete JSON line.
        os.write(fd, payload)
    except (BlockingIOError, BrokenPipeError):
        pass
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print samples for testing instead of using the named pipe.",
    )
    args = parser.parse_args()

    try:
        for sample in samples():
            if args.stdout:
                print(json.dumps(sample), flush=True)
            else:
                write_to_fifo(sample)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
