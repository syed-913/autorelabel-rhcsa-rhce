#!/usr/bin/env bash
# Common mistake: only editing /etc/default/grub (BLS entries are not updated).
sed -i "s/^GRUB_CMDLINE_LINUX=\"\(.*\)\"/GRUB_CMDLINE_LINUX=\"\1 $P_ARG\"/" /etc/default/grub
