## Key-only login for one user

On node1, as the user:

```bash
su - {{user}}
ssh-keygen -t ed25519 -N ''
ssh-copy-id {{user}}@node2
```

On node2, a drop-in that matches only that user:

```bash
cat > /etc/ssh/sshd_config.d/50-{{user}}.conf <<'X'
Match User {{user}}
    PasswordAuthentication no
X
sshd -t && systemctl reload sshd
sshd -T -C user={{user}},host=x,addr=1.2.3.4 | grep passwordauthentication   # no
```

Files in `sshd_config.d/` are read in order and the **first** value of a setting wins, so a global
`PasswordAuthentication no` would affect everyone. A `Match` block keeps it to one user.

References: RHEL 10 *Securing networks* → OpenSSH; `man sshd_config` (`Match`).
