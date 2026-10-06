#!/usr/bin/env bash
sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config
grubby --update-kernel=ALL --args="enforcing=0"
