#!/usr/bin/env bash
# Common mistake: fixing the obvious bugs but not the inverted test.
sed -i 's/-gt 1/-lt 1/; s/done < "\$2"/done < "$1"/' /home/student/scripts/check-hosts.sh
