#!/usr/bin/env bash
# The service was started again by hand while looking into it, so this boot's journal holds
# its messages twice, and that is what "from the current boot" then means.
systemctl restart "$P_WORD-batch.service"
journalctl -b -u "$P_WORD-batch.service" -p err -o cat --no-pager > "/root/$P_WORD-errors.txt"
echo /var/log/messages > "/root/$P_WORD-logfile.txt"
