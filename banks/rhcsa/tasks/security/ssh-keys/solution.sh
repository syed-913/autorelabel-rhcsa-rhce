#!/usr/bin/env bash
sudo -u "$P_USER" ssh-keygen -q -t ed25519 -N '' -f "/home/$P_USER/.ssh/id_ed25519"
ar_ssh_copy_id "$P_USER" "$P_USER@$LAB_NODE2_IP" "$P_PASSWORD"
