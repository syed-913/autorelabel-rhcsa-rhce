#!/usr/bin/env bash
# Common mistake: tuned was disabled; starting it without enabling loses the profile at boot.
systemctl start tuned
tuned-adm recommend > /root/tuned-recommended.txt
tuned-adm profile "$P_PROFILE"
