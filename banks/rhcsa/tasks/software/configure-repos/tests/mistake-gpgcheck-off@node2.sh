#!/usr/bin/env bash
# Common mistake: disabling signature checking to "make it work".
cat > /etc/yum.repos.d/lab.repo <<REPO
[BaseOS]
name=BaseOS
baseurl=$LAB_REPO_BASEOS
gpgcheck=0
[AppStream]
name=AppStream
baseurl=$LAB_REPO_APPSTREAM
gpgcheck=0
REPO
