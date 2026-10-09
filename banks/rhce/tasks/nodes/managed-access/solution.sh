#!/usr/bin/env bash
runuser -u student -- bash -c 'ls ~/.ssh/id_*.pub >/dev/null 2>&1 || ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519'
for h in $LAB_GROUPS_ALL; do
  ar_ssh_copy_id student "ansible@$h.lab.example.com" "$AR_ANSIBLE_PASSWORD"
  runuser -u student -- ssh -o BatchMode=yes "ansible@$h.lab.example.com" \
    "echo '$AR_ANSIBLE_PASSWORD' | sudo -S -p '' bash -c 'echo \"ansible ALL=(ALL) NOPASSWD: ALL\" > /etc/sudoers.d/ansible && chmod 0440 /etc/sudoers.d/ansible && visudo -cq'"
done
