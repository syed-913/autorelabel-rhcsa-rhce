## Groups and memberships

```bash
groupadd -g {{gid}} {{newgroup}}
usermod -aG {{newgroup}} {{u1}}; usermod -aG {{newgroup}} {{u2}}   # or: gpasswd -M {{u1}},{{u2}} {{newgroup}}
gpasswd -d {{u2}} {{oldgroup}}                                     # remove one member
groupmod -n {{renamed}} legacy-{{renamed}}                          # rename, GID unchanged
getent group {{newgroup}} {{oldgroup}} {{renamed}}
```

**Classic mistake:** deleting and recreating a group instead of renaming it. The GID changes,
and files owned by the old GID become orphaned.

References: RHEL 10 *Managing users and groups*; `man gpasswd`, `man groupmod`.
