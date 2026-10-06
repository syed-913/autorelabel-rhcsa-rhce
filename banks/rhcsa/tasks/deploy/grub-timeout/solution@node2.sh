#!/usr/bin/env bash
sed -i "s/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=$P_TIMEOUT/" /etc/default/grub
grub2-mkconfig -o /boot/grub2/grub.cfg >/dev/null 2>&1
