#!/usr/bin/env bash
# Reference solution (run on node1 and node2).
cat > /etc/yum.repos.d/lab.repo <<REPO
[BaseOS]
name=RHEL 10 BaseOS
baseurl=$LAB_REPO_BASEOS
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release

[AppStream]
name=RHEL 10 AppStream
baseurl=$LAB_REPO_APPSTREAM
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
REPO
dnf -q makecache
