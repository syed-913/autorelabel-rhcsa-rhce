#!/usr/bin/env bash
echo "$P_MINUTE $P_HOUR * * $P_DOW logger -t $P_WORD \"scheduled job ran\"" | crontab -u "$P_USER" -
