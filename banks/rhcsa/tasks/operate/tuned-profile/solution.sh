#!/usr/bin/env bash
systemctl enable --now tuned
tuned-adm recommend > /root/tuned-recommended.txt
tuned-adm profile "$P_PROFILE"
