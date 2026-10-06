#!/usr/bin/env bash
cat > /etc/yum.repos.d/extras.repo <<REPO
[extras]
name=Lab extras
baseurl=http://$LAB_UTILITY_FQDN/extras/
enabled=1
gpgcheck=0
REPO
dnf -y -q upgrade labtools
