#!/usr/bin/env bash
# Common mistake: "fixing" it by turning SELinux off.
setenforce 0
sed -i 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config
