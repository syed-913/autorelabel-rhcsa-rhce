#!/usr/bin/env bash
# Common mistake: hour and minute swapped.
echo "$P_HOUR $P_MINUTE * * $P_DOW logger -t $P_WORD \"scheduled job ran\"" | crontab -u "$P_USER" -
