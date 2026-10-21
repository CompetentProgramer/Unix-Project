# Dashboard

Tkinter + matplotlib window that shows live and historical charts for every agent,
with adjustable alert thresholds. Run it on the machine whose public IP is allowed
through the firewall (see `docs/COMMANDS.md`, "set-dashboard-ip").

## Setup

1. Find this machine's public IP (https://ifconfig.me) and make sure it is allowed:
   `deploy/gcp_setup.sh set-dashboard-ip <IP>` (run in the Codespace).
2. Install the libraries: `pip install -r requirements.txt`.
   On Linux also `sudo apt install python3-tk`; Windows and macOS include Tkinter.
3. `cp servers_example.yaml servers.yaml`, then put each server's real API key in it
   (`sudo grep OBS_API_KEY /etc/obs-agent/agent.env` on that VM).
   **`servers.yaml` is gitignored. Never commit it or paste keys into code.**
4. `python Dashboard.py` (from this folder; collection starts as soon as it opens).

`servers.yaml` format:

```yaml
server1:
  api_url: "http://<VM1 external IP>:8090"
  api_key: "<VM1 key>"
server2:
  api_url: "http://<VM2 external IP>:8090"
  api_key: "<VM2 key>"
```

A list layout (`servers:` with `name`, `host`, `port`, `api_key`) also works.

## Using it

- Buttons at the top switch servers and show each one's state:
  OK, STALE (agent answers but sends no new data), DOWN (no answer) or WAITING.
- "Time window" switches between the last 2 minutes, 10 minutes, hour and 6 hours.
  History is saved in `history.db` (gitignored) and survives restarts. After an outage
  the gap is refilled from the agent's one-hour buffer where possible.
- Type limits into the threshold boxes and press "Set thresholds". A limit shows as a red
  dashed line, and the bar turns red naming the server and metric that crossed it.
  A DOWN server also raises the alert. Limits are saved in `thresholds.json` (gitignored).
- The bottom bar shows each server's last error.

## Troubleshooting

| Bar says | Meaning |
| --- | --- |
| no response (firewall rule, ...) | Wrong IP, or this machine's public IP is not allowed. Run `set-dashboard-ip`. |
| connection refused (agent stopped?) | VM is up but the agent is not; the watchdog or systemd restarts it. |
| 401: wrong API key | The key in `servers.yaml` does not match `/etc/obs-agent/agent.env` on that VM. |
| agent has no samples yet | Agent just started; wait a few seconds. |
