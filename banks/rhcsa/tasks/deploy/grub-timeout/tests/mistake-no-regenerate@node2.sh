#!/usr/bin/env bash
# Common mistake: editing /etc/default/grub without regenerating grub.cfg.
sed -i "s/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=$P_TIMEOUT/" /etc/default/grub
