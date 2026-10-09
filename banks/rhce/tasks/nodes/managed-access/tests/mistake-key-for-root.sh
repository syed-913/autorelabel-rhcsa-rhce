#!/usr/bin/env bash
# Common mistake: the key pair is created and copied as root on control, not as the candidate user.
test -f /root/.ssh/id_ed25519 || ssh-keygen -q -t ed25519 -N "" -f /root/.ssh/id_ed25519
for h in $LAB_GROUPS_ALL; do
  ar_ssh_copy_id root "ansible@$h.lab.example.com" "$AR_ANSIBLE_PASSWORD"
  ssh -o BatchMode=yes "ansible@$h.lab.example.com" \
    "echo '$AR_ANSIBLE_PASSWORD' | sudo -S -p '' bash -c 'echo \"ansible ALL=(ALL) NOPASSWD: ALL\" > /etc/sudoers.d/ansible && chmod 0440 /etc/sudoers.d/ansible'"
done
