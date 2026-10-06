#!/usr/bin/env bash
# Common mistake: grepping for the word "err"/exact priority instead of "err or higher".
journalctl -b -u "$P_WORD-batch.service" -p err..err -o cat --no-pager > "/root/$P_WORD-errors.txt"
echo /var/log/messages > "/root/$P_WORD-logfile.txt"
