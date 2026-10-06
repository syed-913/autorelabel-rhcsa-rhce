## Work as root through sudo

```bash
ssh {{user}}@node2              # or su - {{user}}
sudo touch /root/{{word}}-by-sudo
sudo -i                         # a full root login shell, if you need several commands
```

Every sudo command is logged in `/var/log/secure` (and the journal), which is how admins (and this
grader) see who did what.

References: `man sudo`.
