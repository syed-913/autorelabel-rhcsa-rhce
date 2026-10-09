#!/usr/bin/env bash
# Common mistake: %U (week of year, Sunday-based) is not the ISO week (%V).
printf '#!/bin/bash\ndate +%%U\n' > /usr/local/bin/isoweek
chmod 0755 /usr/local/bin/isoweek
rpm -qd chrony | grep -m1 '/NEWS' > /root/chrony-news.txt
