#!/usr/bin/env bash
printf '#!/bin/bash\ndate +%%V\n' > /usr/local/bin/isoweek
chmod 0755 /usr/local/bin/isoweek
# not `rpm -qd | grep -m1`: grep exiting early can kill rpm with SIGPIPE (pipefail)
docs="$(rpm -qd chrony)"; grep -m1 '/NEWS' <<<"$docs" > /root/chrony-news.txt
