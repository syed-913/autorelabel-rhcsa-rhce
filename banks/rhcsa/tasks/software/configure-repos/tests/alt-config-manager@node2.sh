#!/usr/bin/env bash
# Valid alternative: dnf config-manager plus importing the key into the RPM database.
dnf config-manager --add-repo "$LAB_REPO_BASEOS" >/dev/null
dnf config-manager --add-repo "$LAB_REPO_APPSTREAM" >/dev/null
rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
