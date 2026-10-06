## Key-based SSH login

Work **as the user**, on node1:

```bash
su - {{user}}
ssh-keygen -t ed25519 -N ''            # empty passphrase: no prompt at login
ssh-copy-id {{user}}@node2             # asks for {{user}}'s password on node2 once
ssh {{user}}@node2 hostname            # no password prompt now
```

`ssh-copy-id` appends the public key to `~{{user}}/.ssh/authorized_keys` on node2 with the right
permissions (700 on `.ssh`, 600 on the file) and SELinux label.

**Classic mistakes:** generating or copying the key as root (it then authorizes root's key, not
{{user}}'s); a passphrase-protected key (still a prompt); copying the file by hand with wrong
permissions (sshd ignores it).

References: RHEL 10 *Securing networks* → OpenSSH key pairs; `man ssh-keygen`, `man ssh-copy-id`.
