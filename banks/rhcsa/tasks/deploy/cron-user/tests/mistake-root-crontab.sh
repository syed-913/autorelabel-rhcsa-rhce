#!/usr/bin/env bash
# Common mistake: putting the job in root's crontab.
echo "$P_MINUTE $P_HOUR * * $P_DOW logger -t $P_WORD \"scheduled job ran\"" | crontab -
