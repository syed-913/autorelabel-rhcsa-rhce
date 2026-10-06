#!/usr/bin/env bash
# Common mistake: user crontab syntax (no user field) in /etc/cron.d.
echo "*/$P_EVERY * * * * /usr/bin/logger -t $P_WORD \"system job\"" > /etc/cron.d/lab-$P_WORD
