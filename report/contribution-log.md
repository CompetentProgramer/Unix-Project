# Contribution log

One line per finished piece of work. This feeds the report's individual contribution table
(activity type and percentage of effort per member).

Activity types: Cloud setup, Security, Agent/API, Stress script, Systemd/cron, Dashboard,
Testing, Documentation, Report, Video.

| Date | Member | Activity type | What was done | Approx. hours |
| --- | --- | --- | --- | --- |
| 2026-10-18 | Member 4 | Cloud setup | Created obs-vpc, subnet and the vm command | 2 |
| 2026-10-18 | Member 4 | Security | Setup firewall controls for VMs | 3 |
| 2026-10-18 | Member 2 | Stress script | wrote stress_loop.sh and published stress state to state.json for the dashboard| 1 |
| 2026-10-18 | Member 2 | Systemd/cron | Wrote obs-stress.service, watchdog.sh and the cron job; tested crash and hang recovery| 1.5 |
| 2026-10-18 | Member 3 | Dashboard | Created Dashboard app using python; Integrated threshold notifier; Created server poller| 4.5 |
| 2026-10-19 | Member 4 | Testing | Troubleshooting problems for final code | 2 |
| 2026-10-20/21 | Member 4 | Testing | Troubleshooting problems for final code. Again... | 5 |
| 2026-10-17 | Member 1 | Cloud Setup | Created the GCP project and set permissions for every user. Understood the requirements of the Project and started necessary research | 1 |
| 2026-10-17 | Member 1 | Agent folder|Created the whole /agent folder. Developed the five-metric collector, named-pipe communication, API endpoints, launcher script, and agent systemd service.| 4 |
| 2026-10-17 | Member 1 | Tests | Passed all five API verification checks and confirmed automatic service recovery after killing the collector..| 1 |




## Final effort summary

| Member | Main activities | % of effort |
| --- | --- | --- |
| Member 1 |  Metrics and API Developed | 25% |
| Member 2 | Stress script and Systemd/cron | 25% |
| Member 3 | Dashboard App | 25% |
| Member 4 | Firewall and setup | 25% |
| **Total** | | **100%** |
