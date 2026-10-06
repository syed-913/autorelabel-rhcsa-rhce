#!/usr/bin/env bash
firewall-cmd --set-default-zone="$P_ZONE"
firewall-cmd --permanent --zone="$P_ZONE" --add-service=https
firewall-cmd --permanent --zone="$P_ZONE" --add-service=ssh
firewall-cmd --reload
