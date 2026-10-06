#!/usr/bin/env bash
# Valid alternative: /etc/default/grub plus regenerating with --update-bls-cmdline.
sed -i "s/^GRUB_CMDLINE_LINUX=\"\(.*\)\"/GRUB_CMDLINE_LINUX=\"\1 $P_ARG\"/" /etc/default/grub
grub2-mkconfig -o /boot/grub2/grub.cfg --update-bls-cmdline >/dev/null 2>&1
