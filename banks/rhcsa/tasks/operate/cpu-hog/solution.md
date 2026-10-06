## A CPU-hungry process

```bash
top                                   # or: ps -eo pid,comm,%cpu --sort=-%cpu | head
ps -o comm= -p <PID> > /root/cpu-hog.txt
systemctl status <PID>                # shows which unit started it: {{word}}-worker.service
systemctl disable --now {{word}}-worker.service   # (mask also works)
```

**Classic mistake:** `kill`/`pkill` alone. The unit has `Restart=always`, so systemd starts it
again within seconds, and it is still enabled at boot.

References: RHEL 10 *Monitoring and managing system status and performance*; `man ps`, `man systemctl`.
