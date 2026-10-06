#!/usr/bin/env bash
# Common mistake: killing the PID; systemd restarts it (and it starts again at boot).
ps -eo comm --sort=-%cpu | sed -n 2p > /root/cpu-hog.txt
pkill -9 -x "${P_WORD}d"
