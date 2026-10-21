# Interfaces between team members

Everyone codes against these fixed values so the pieces fit on the first deploy.
Change one only by agreeing in the team chat and editing this file in the same pull request.

## On each VM

| Item | Value |
| --- | --- |
| Agent user and group | `obs-agent` (system account, `nologin`) |
| Stress user | `obs-stress` (separate account) |
| Code location | `/opt/obs-agent/{agent,stress,deploy}` (root-owned, read-only to services) |
| API port | `8090` (TCP) |
| API key | env var `OBS_API_KEY`, loaded from `/etc/obs-agent/agent.env` (`root:obs-agent`, mode 640) |
| Named pipe | `/run/obs-agent/metrics.fifo` (mode 660, `obs-agent:obs-agent`) |
| Runtime dirs | `RuntimeDirectory=obs-agent` and `RuntimeDirectory=obs-stress` in the units |
| Stress scratch dir | `/var/tmp/obs-stress` (owned by `obs-stress`) |
| Watchdog log | `/var/log/obs-watchdog.log` |

## Files `deploy/setup_vm.sh` expects in the repo

| Path | Owner | Requirements |
| --- | --- | --- |
| `agent/obs-agent.service` | Member 1 | `EnvironmentFile=/etc/obs-agent/agent.env`, `User=obs-agent`, `RuntimeDirectory=obs-agent`, `Restart=always` |
| `agent/run_agent.sh` | Member 1 | Starts the collector and the API process |
| `stress/obs-stress.service` | Member 2 | `Type=notify`, `NotifyAccess=all`, `Restart=always`, `WatchdogSec`, `User=obs-stress` |
| `stress/stress_loop.sh` | Member 2 | Pings `systemd-notify WATCHDOG=1` while `stress-ng` runs |
| `agent/watchdog.sh` | Member 2 | Run as root by cron every 5 minutes; must be executable |

## API contract (Member 1 serves, Member 3 consumes)

Base URL: `http://<VM external IP>:8090`

| Endpoint | Key needed | Success response |
| --- | --- | --- |
| `GET /health` | No | `200` `{"status": "ok", "age_s": 1.2}`; `status` is `stale` if the newest sample is over 10 s old |
| `GET /metrics` | Yes | `200` newest sample (below) |
| `GET /history?seconds=N` | Yes | `200` `{"samples": [ ...samples, oldest first... ]}` |

A missing or wrong `X-API-Key` header returns **401** `{"error": "unauthorized"}`.

Sample format (all numbers):

```json
{"ts": 1760800000, "cpu_percent": 12.5, "mem_percent": 41.0,
 "disk_io_mbps": 0.8, "net_kbps": 5.2, "load_1m": 0.31}
```

| Field | Meaning | Unit |
| --- | --- | --- |
| `ts` | Time of the sample | Unix seconds (UTC) |
| `cpu_percent` | CPU use, all cores | % (0-100) |
| `mem_percent` | Memory in use | % (0-100) |
| `disk_io_mbps` | Disk read + write rate | MB/s |
| `net_kbps` | Network sent + received rate, all interfaces including loopback | KB/s |
| `load_1m` | 1-minute load average | load |

Optional extra: while a stress event runs, Member 2 writes `/run/obs-stress/state.json`
(`{"class": "cpu", "started": 1760800000, "ends": 1760800060}`) and Member 1 adds it to
`/metrics` as `"stress"`, so the dashboard can shade stress windows.

`deploy/verify.sh` tests exactly this contract (health open, key enforced).

## Dashboard config (Member 3)

`dashboard/servers.yaml` is **not committed** (it holds API keys; it is in `.gitignore`).
Commit `dashboard/servers_example.yaml` instead, with placeholder keys:

```yaml
server1:
  api_url: "http://203.0.113.10:8090"
  api_key: "<API_KEY_GOES_HERE>"
```

Run `python Dashboard.py` from the `dashboard/` folder. See `dashboard/README.md`.

## Network (Member 4)

- Only the dashboard machine's public IP may reach port 8090, enforced twice:
  GCP firewall rule `obs-allow-agent` and host `iptables` chain `OBS_AGENT`.
- SSH is only reachable through Google IAP (`--tunnel-through-iap`).
- API keys are generated per VM by `setup_vm.sh` and shared privately, never in the repo.