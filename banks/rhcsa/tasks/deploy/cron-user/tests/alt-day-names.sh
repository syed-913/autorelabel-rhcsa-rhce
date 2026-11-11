#!/usr/bin/env bash
# Days of the week by name, which cron accepts as well as numbers.
case "$P_DOW" in
  1-5) days=mon-fri ;;
  1,3,5) days=Mon,Wed,Fri ;;
  6,0) days=sat,sun ;;
  *) days="$P_DOW" ;;
esac
echo "$P_MINUTE $P_HOUR * * $days logger -t $P_WORD \"scheduled job ran\"" | crontab -u "$P_USER" -
