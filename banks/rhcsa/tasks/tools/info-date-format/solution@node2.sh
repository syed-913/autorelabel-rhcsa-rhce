#!/usr/bin/env bash
printf '#!/bin/bash\ndate +%%V\n' > /usr/local/bin/isoweek
chmod 0755 /usr/local/bin/isoweek
rpm -qd chrony | grep -m1 '/NEWS' > /root/chrony-news.txt
