"""Talk to the agent APIs.

Servers come from servers.yaml (never committed; see servers_example.yaml).
Nothing here raises on a network problem: every call returns (result, error)
so one dead server can never freeze or crash the dashboard.
"""

import math
import os
import re
from pathlib import Path

import requests
import yaml

HERE = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("OBS_SERVERS", HERE / "servers.yaml"))
TIMEOUT_S = 3  # a stopped or blocked server must not hang the window

FIELDS = (
    "ts",
    "cpu_percent",
    "mem_percent",
    "disk_io_mbps",
    "net_kbps",
    "load_1m",
)


class ConfigError(Exception):
    """servers.yaml is missing or wrong."""


def _pretty_name(key, number):
    """server1 -> 'Server 1'; anything else is used as written."""
    match = re.fullmatch(r"server\s*_?(\d+)", str(key), flags=re.IGNORECASE)
    return f"Server {match.group(1)}" if match else str(key or f"Server {number}")


def load_servers(path=CONFIG_PATH):
    """Return a list of {"name", "base", "key"} dicts from servers.yaml.

    Two layouts are accepted:
      server1: {api_url: "http://IP:8090", api_key: "..."}     (team format)
      servers: [{name, host, port, api_key}, ...]                (list format)
    """
    try:
        # utf-8-sig: Windows editors often add a byte-order mark
        with open(path, encoding="utf-8-sig") as handle:
            raw = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        raise ConfigError(
            f"{path} not found. Copy servers_example.yaml to servers.yaml "
            "and fill in each server's API key."
        )
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}")

    if not isinstance(raw, dict) or not raw:
        raise ConfigError(f"{path} is empty or not in the expected format")
    if isinstance(raw.get("servers"), list):
        entries = [(None, entry) for entry in raw["servers"]]
    else:
        entries = list(raw.items())

    servers = []
    for number, (key_name, entry) in enumerate(entries, start=1):
        if not isinstance(entry, dict) or "api_key" not in entry:
            raise ConfigError(f"server {number} needs api_key and api_url (or host)")
        api_key = str(entry["api_key"]).strip()
        if entry.get("api_url"):
            base = str(entry["api_url"]).strip().rstrip("/")
            if not base.startswith("http"):
                base = "http://" + base
        elif entry.get("host"):
            base = f"http://{str(entry['host']).strip()}:{int(entry.get('port', 8090))}"
        else:
            raise ConfigError(f"server {number} needs api_url (or host and port)")
        name = str(entry.get("name") or _pretty_name(key_name, number))
        if not api_key or api_key.startswith("<") or api_key == "REPLACE_ME":
            raise ConfigError(f"{name} still has a placeholder API key in servers.yaml")
        servers.append({"name": name, "base": base, "key": api_key})
    return servers


def get_json(server, endpoint, params=None):
    """GET one endpoint. Returns (data, None) or (None, short error text)."""
    try:
        reply = requests.get(
            server["base"] + endpoint,
            params=params,
            headers={"X-API-Key": server["key"]},
            timeout=TIMEOUT_S,
        )
    except requests.exceptions.Timeout:
        return None, "no response (firewall rule, your public IP, or VM stopped?)"
    except requests.exceptions.ConnectionError:
        return None, "connection refused (agent stopped?)"
    except requests.exceptions.RequestException as exc:
        return None, f"request failed ({exc.__class__.__name__})"

    if reply.status_code == 200:
        try:
            return reply.json(), None
        except ValueError:
            return None, "reply was not JSON"
    if reply.status_code == 401:
        return None, "401: wrong API key"
    if reply.status_code == 503:
        return None, "agent has no samples yet"
    return None, f"HTTP {reply.status_code}"


def clean_sample(sample):
    """Return a sample with every field as a finite float, or None."""
    try:
        cleaned = {field: float(sample[field]) for field in FIELDS}
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in cleaned.values()):
        return None
    return cleaned


def fetch_latest(server):
    """Newest sample: (sample, None) or (None, error)."""
    data, error = get_json(server, "/metrics")
    if data is None:
        return None, error
    sample = clean_sample(data)
    if sample is None:
        return None, "malformed sample from agent"
    return sample, None


def fetch_history(server, seconds):
    """Samples from the last `seconds`, oldest first: (list, None) or (None, error)."""
    data, error = get_json(server, "/history", params={"seconds": int(seconds)})
    if data is None:
        return None, error
    raw = data.get("samples") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None, "malformed history from agent"
    samples = [s for s in (clean_sample(item) for item in raw) if s is not None]
    return samples, None
