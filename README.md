# Linux Infrastructure Observability Dashboard

Four GCP Ubuntu VMs, each running a custom Python metrics agent and a `stress-ng` load
generator, monitored by one custom Dash dashboard. No off-the-shelf monitoring tools are used.
The original assignment is in `docs/ASSIGNMENT.md`.

## Layout

```text
agent/       collector, API process, launcher, systemd unit, cron watchdog   (Member 1 / 2)
stress/      stress_loop.sh and its systemd unit                             (Member 2)
dashboard/   Dash app, poller, SQLite code                                   (Member 3)
deploy/      GCP, VM and firewall scripts, watchdog cron file                (Member 4)
docs/        INTERFACES.md (contract between pieces), COMMANDS.md, assignment
report/      screenshots and the contribution log for the final report
```

## Quick start (deployment)

One teammate sets up the shared network once; everyone else skips to step 3.
Run steps 1 to 3 in the Codespace, and steps 4 and 5 on the VM.

```bash
# 1. Network (once)
deploy/gcp_setup.sh network

# 2. Firewall: allow the agent port from the dashboard's public IP only
deploy/gcp_setup.sh firewall <DASHBOARD_PUBLIC_IP>

# 3. Your VM (N = your member number, 1-4)
deploy/gcp_setup.sh vm N

# 4. On the VM
gcloud compute ssh obs-srv-N --zone us-central1-a --tunnel-through-iap
git clone https://github.com/CompetentProgramer/Unix-Project && cd Unix-Project
sudo deploy/setup_vm.sh <DASHBOARD_PUBLIC_IP>

# 5. From the dashboard machine
deploy/verify.sh <VM_IP> <API_KEY>
```

Use a public IP, not a private one (10.x, 172.16-31.x, 192.168.x); private addresses never
match internet traffic. Put `DRY_RUN=1` before `deploy/gcp_setup.sh` to print the `gcloud`
commands without running them.

If the dashboard's public IP changes (new network, VPN), run
`deploy/gcp_setup.sh set-dashboard-ip <NEW_IP>`. It updates the GCP firewall and the
`iptables` rules on every running VM.

After pulling new code, rerun `sudo deploy/setup_vm.sh <DASHBOARD_PUBLIC_IP>` on each VM.
It is safe to rerun and keeps the existing API key. See `docs/COMMANDS.md` for every command.

## Security

- GCP firewall: TCP 8090 only from the dashboard IP; SSH only from the IAP range.
- `iptables` chain `OBS_AGENT` on each VM repeats the same restriction.
- Every VM has its own API key (`/etc/obs-agent/agent.env`). Never commit or paste keys.

## Git workflow

- `main` always works. Work on a branch named `area/short-description`
  (for example `agent/named-pipe`) and merge by pull request, reviewed by a teammate.
- Small commits with an imperative message that says what changed and why.
- Never commit API keys, `servers.yaml`, or `*.db` files (see `.gitignore`).
- Add a line to `report/contribution-log.md` when you finish a piece of work.