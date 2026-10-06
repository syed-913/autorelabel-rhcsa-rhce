#!/usr/bin/env bash
# Valid alternative: UMASK in /etc/login.defs (applied by pam_umask at login), with root's
# umask kept at 0022 explicitly.
sed -i 's/^UMASK.*/UMASK\t\t027/' /etc/login.defs
echo 'umask 022' >> /root/.bashrc
