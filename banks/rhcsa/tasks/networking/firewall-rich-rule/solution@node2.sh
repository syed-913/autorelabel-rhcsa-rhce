#!/usr/bin/env bash
firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$LAB_NODE1_IP/32 service name=http accept"
firewall-cmd --reload
