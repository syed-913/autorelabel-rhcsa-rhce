#!/usr/bin/env bash
ps -eo comm --sort=-%cpu | sed -n 2p > /root/cpu-hog.txt
systemctl disable --now "$P_WORD-worker.service"
