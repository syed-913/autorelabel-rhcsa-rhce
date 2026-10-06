## Tuning profiles

```bash
systemctl enable --now tuned
tuned-adm recommend > /root/tuned-recommended.txt
tuned-adm list
tuned-adm profile {{profile}}
tuned-adm active
```

The active profile is stored by tuned and reapplied at boot, **if** the tuned service is enabled.

References: RHEL 10 *Monitoring and managing system status and performance* → TuneD;
`man tuned-adm`.
