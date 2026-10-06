## Default permissions for all users

Use a script in `/etc/profile.d/`, which every login shell reads, and keep root at the default:

```bash
cat > /etc/profile.d/umask-users.sh <<'SH'
if [ "$(id -u)" -ge 1000 ]; then
    umask 027
fi
SH
su - {{user1}} -c umask      # 0027
su - root -c umask           # 0022
```

Alternatively set `UMASK 027` in `/etc/login.defs` (applied by `pam_umask` at login), and make
sure root still ends up with 0022.

**Classic mistake:** editing only the existing users' `~/.bashrc`. Users created later won't
get it (unless you also changed `/etc/skel`).

References: RHEL 10 *Managing file systems* → default umask; `man login.defs`, `man pam_umask`.
