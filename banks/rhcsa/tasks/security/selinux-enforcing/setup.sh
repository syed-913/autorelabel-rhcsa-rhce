#!/usr/bin/env bash
sed -i 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config
setenforce 0
