#!/usr/bin/env bash
# Common mistake: pointing at the top of the DVD tree instead of BaseOS/AppStream.
cat > /etc/yum.repos.d/lab.repo <<REPO
[dvd]
name=DVD
baseurl=${LAB_REPO_BASEOS%/BaseOS}
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
REPO
