#!/usr/bin/env bash
journalctl -b -u "$P_WORD-batch.service" -p err -o cat --no-pager > "/root/$P_WORD-errors.txt"
echo /var/log/messages > "/root/$P_WORD-logfile.txt"
