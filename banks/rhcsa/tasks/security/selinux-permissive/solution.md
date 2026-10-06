## SELinux permissive mode

```bash
setenforce 0                                                    # now
sed -i 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config  # persistent
getenforce
```

Permissive mode still loads the policy and logs denials (useful for troubleshooting with
`ausearch -m AVC`), but does not block anything.

**Classic mistakes:** `setenforce 0` alone (back to enforcing after a reboot); `SELINUX=disabled`
(SELinux is switched off entirely, and turning it on again later needs a full relabel).

References: RHEL 10 *Using SELinux* → "Changing to permissive mode".
