## SSH keys and privilege escalation for the managed nodes

As `{{lab.control_user}}` on control:

```bash
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519      # once
for h in node1 node2 node3; do                         # every managed node in your lab
  ssh-copy-id ansible@$h.lab.example.com               # asks for the ansible password
done
```

Then the sudo rule, either on each node:

```bash
ssh ansible@node1.lab.example.com
sudo -i                                                # ansible's password
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/ansible
chmod 0440 /etc/sudoers.d/ansible; visudo -c
```

or for all nodes at once with an ad-hoc command (asks for the become password once):

```bash
ansible all -K -m ansible.builtin.copy \
  -a "dest=/etc/sudoers.d/ansible content='ansible ALL=(ALL) NOPASSWD: ALL\n' mode=0440 validate='visudo -cf %s'"
ansible all -m ansible.builtin.ping                    # must answer pong everywhere, no prompts
ansible all -a 'id' -b                                  # uid=0(root)
```

**Classic mistakes:** creating the key as root (`sudo ssh-keygen`), so `{{lab.control_user}}`
still needs a password; a sudo rule without `NOPASSWD`, so every playbook needs `-K`; an
unvalidated sudoers file that locks `ansible` out of sudo completely (always `visudo -c`).

References: RHEL 10 *Managing sudo access*; `man ssh-copy-id`, `man sudoers`.
