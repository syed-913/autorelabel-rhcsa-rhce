#!/usr/bin/env bash
# Common mistake: allowing http for everyone.
firewall-cmd --permanent --add-service=http; firewall-cmd --reload
