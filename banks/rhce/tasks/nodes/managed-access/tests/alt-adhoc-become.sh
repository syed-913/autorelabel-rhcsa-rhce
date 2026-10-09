#!/usr/bin/env bash
# Valid alternative: keys with ssh-copy-id, then the sudo rule with an ad-hoc command
# that asks for the become password once (given here as an extra variable).
runuser -u student -- bash -c 'ls ~/.ssh/id_*.pub >/dev/null 2>&1 || ssh-keygen -q -t rsa -b 3072 -N "" -f ~/.ssh/id_rsa'
for h in $LAB_GROUPS_ALL; do ar_ssh_copy_id student "ansible@$h.lab.example.com" "$AR_ANSIBLE_PASSWORD"; done
as_student ansible all -m ansible.builtin.copy \
  -a "dest=/etc/sudoers.d/ansible content='ansible ALL=(ALL) NOPASSWD: ALL\n' mode=0440 validate='visudo -cf %s'" \
  -e "ansible_become_password=$AR_ANSIBLE_PASSWORD"
