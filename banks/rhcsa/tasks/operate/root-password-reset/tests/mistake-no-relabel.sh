#!/usr/bin/env bash
# Common mistake: password changed from the rd.break chroot without `touch /.autorelabel`.
# passwd in the chroot creates a new /etc/shadow with the wrong SELinux label.
echo "root:$P_NEW_PASSWORD" | chpasswd
chcon -t unlabeled_t /etc/shadow
