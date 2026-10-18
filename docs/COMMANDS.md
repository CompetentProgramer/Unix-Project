# Operating commands

Where you run a command matters. **Codespace** = talks to GCP. **VM** = talks to one server.
**Dashboard machine** = the laptop or VM that runs the dashboard.

## Codespace: GCP

```bash
gcloud auth login --no-launch-browser           # sign in (once)
gcloud config set project linux-observability   # pick the shared project (once)

deploy/gcp_setup.sh network                     # VPC + subnet (once per team)
deploy/gcp_setup.sh firewall IP [IP...]         # who may reach port 8090
deploy/gcp_setup.sh vm N                        # your static IP + VM obs-srv-N
deploy/gcp_setup.sh set-dashboard-ip IP [IP...] # firewall + every running VM's iptables
DRY_RUN=1 deploy/gcp_setup.sh <command> ...     # print the gcloud commands only

gcloud compute instances list                   # all VMs, IPs, status
gcloud compute instances stop  obs-srv-N --zone us-central1-a
gcloud compute instances start obs-srv-N --zone us-central1-a
gcloud compute ssh obs-srv-N --zone us-central1-a --tunnel-through-iap
gcloud compute firewall-rules list --filter="network:obs-vpc" \
  --format="table(name,sourceRanges.list(),allowed[].map().firewall_rule().list(),targetTags.list())"
```

## VM: setup and firewall

```bash
cd ~/Unix-Project && git pull                   # always pull before running anything
sudo deploy/setup_vm.sh IP [IP...]              # full VM setup (safe to re-run)
sudo deploy/iptables.sh IP [IP...]              # only the host firewall
sudo iptables -L OBS_AGENT -n -v                # check the rules and packet counts
sudo ls -l /etc/obs-agent/agent.env             # key file exists, mode 640
id obs-agent obs-stress                         # both service accounts exist
```

Rotate an API key: `sudo rm /etc/obs-agent/agent.env && sudo deploy/setup_vm.sh IP [IP...]`

## VM: services (once Members 1 and 2 add their units)

```bash
systemctl status obs-agent obs-stress           # running? enabled?
sudo systemctl restart obs-agent                # or start / stop
sudo journalctl -u obs-agent -n 50 --no-pager   # last log lines
sudo journalctl -u obs-stress -f                # follow live (Ctrl+C to stop)

# Demo: crash the agent; systemd (Restart=always) brings it back in seconds
sudo kill -9 "$(systemctl show -p MainPID --value obs-agent)"
sleep 3 && systemctl status obs-agent

# Cron watchdog: a deliberate "systemctl stop" is revived by cron within 5 minutes
sudo systemctl stop obs-agent
sudo /opt/obs-agent/agent/watchdog.sh           # run the check by hand
tail -n 20 /var/log/obs-watchdog.log
cat /etc/cron.d/obs-watchdog

sudo reboot                                     # then SSH back in: services should be up
```

## VM: quick manual tests

```bash
stress-ng --cpu 0 --timeout 30s --metrics-brief          # 30 s of CPU load
curl -s localhost:8090/health                            # open endpoint
KEY="$(sudo grep OBS_API_KEY /etc/obs-agent/agent.env | cut -d= -f2)"
curl -s -H "X-API-Key: $KEY" localhost:8090/metrics      # needs the key
```

## Dashboard machine

```bash
deploy/verify.sh VM_IP API_KEY                  # health open, key enforced
curl -m 5 http://VM_IP:8090/health              # from a NOT-allowed network: must time out
```

## Git

```bash
git pull                                        # start of every session
git checkout -b area/short-description          # new branch per task
git add <files> && git commit -m "Imperative summary of what and why"
git push -u origin area/short-description       # then open a pull request
```

## Demo day runbook

1. Start all four VMs: `gcloud compute instances start obs-srv-N --zone us-central1-a`.
2. On the presenting network, get the dashboard IP at https://ifconfig.me.
3. From the Codespace: `deploy/gcp_setup.sh set-dashboard-ip THAT_IP`.
4. Run `deploy/verify.sh` against each VM, then start the dashboard app.
5. Show the dashboard, trigger a stress event, show the threshold alert.
6. Show the restart: `sudo kill -9 ...` on a VM, then its status a few seconds later.
7. Afterwards, stop the VMs.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `curl` to port 8090 times out from an allowed machine | `gcloud compute firewall-rules list ...` includes your IP; `sudo iptables -L OBS_AGENT -n` includes your IP; agent is running |
| `401` with the right key | Key matches `/etc/obs-agent/agent.env` on that VM; header is `X-API-Key` |
| `insufficient authentication scopes` | You ran a `gcloud` admin command on a VM; run it in the Codespace |
| `IAP` SSH hangs or is refused | Rule `obs-allow-ssh-iap` exists; you have the IAP tunnel role |
| Works on one network, not another | Public IP changed, or the network blocks outbound port 8090 |
| VM unreachable after restart | `gcloud compute instances list` shows `RUNNING`; static IP unchanged |