## Privileged access with sudo

Use a drop-in file and validate it (a broken sudoers file can lock you out of sudo):

```bash
usermod -aG {{group}} {{admin}}
visudo -f /etc/sudoers.d/lab-access
```

```
%{{group}}  ALL=(ALL)  ALL
{{operator}}  ALL=(root)  NOPASSWD: /usr/bin/systemctl restart chronyd
```

```bash
visudo -c
sudo -l -U {{operator}}
```

Commands in sudoers must use **full paths**. `%` marks a group.

**Classic mistakes:** granting `NOPASSWD: ALL` to the operator; editing `/etc/sudoers` without
`visudo` and leaving a syntax error; adding the admin to `wheel` instead of using the requested group.

References: RHEL 10 *Managing sudo access*; `man sudoers` (examples).
