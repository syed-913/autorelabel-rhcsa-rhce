#!/usr/bin/env bash
cat > /usr/local/bin/lab-inventory <<'SH'
#!/bin/bash
case "$1" in
  --summary) echo "summary: 3 disks, 2 nics, 1 cpu";;
  --verbose) echo "verbose: scanning"; echo "warning: sensor 3 unreadable" >&2; echo "verbose: done";;
  *) echo "disk vda 20G"; echo "disk vdb 8G"; echo "error: disk vdz not found" >&2
     echo "nic mgmt0 up"; echo "disk vdc 4G"; echo "error: cdrom tray open" >&2; echo "cpu 1";;
esac
SH
chmod 0755 /usr/local/bin/lab-inventory; restorecon /usr/local/bin/lab-inventory
