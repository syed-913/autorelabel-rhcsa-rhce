#!/usr/bin/env bash
echo "*/$P_EVERY * * * * root /usr/bin/logger -t $P_WORD \"system job\"" > /etc/cron.d/lab-$P_WORD
chmod 0644 /etc/cron.d/lab-$P_WORD
