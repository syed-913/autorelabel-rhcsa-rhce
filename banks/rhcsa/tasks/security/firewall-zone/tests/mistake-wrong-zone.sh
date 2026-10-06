#!/usr/bin/env bash
# Common mistake: changing the default zone but adding https to the old (public) zone.
firewall-cmd --set-default-zone="$P_ZONE"
firewall-cmd --permanent --zone=public --add-service=https
firewall-cmd --reload
