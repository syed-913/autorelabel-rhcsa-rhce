#!/usr/bin/env bash
# Valid alternative: a source-bound zone that allows http only for node1.
firewall-cmd --permanent --new-zone=webclients
firewall-cmd --permanent --zone=webclients --add-source="$LAB_NODE1_IP/32"
firewall-cmd --permanent --zone=webclients --add-service=http
firewall-cmd --permanent --zone=webclients --add-service=ssh
firewall-cmd --reload
