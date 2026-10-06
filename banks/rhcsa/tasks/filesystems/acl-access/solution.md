## Access control lists

```bash
dnf install -y acl
setfacl -m u:{{reader}}:r  /srv/{{word}}/budget.csv
setfacl -m u:{{writer}}:rw /srv/{{word}}/budget.csv
setfacl -m u:{{reader}}:rx,u:{{writer}}:rx /srv/{{word}}      # enter the directory
setfacl -d -m u:{{writer}}:rw /srv/{{word}}                    # default ACL for new files
getfacl /srv/{{word}} /srv/{{word}}/budget.csv
```

`ls -l` shows a `+` after the mode when ACLs exist. The ACL **mask** limits named entries; if a
later `chmod` lowers the group bits, check `getfacl` for `#effective:`.

**Classic mistake:** `chmod o+rw`. Everyone gets access, not just the two users.

References: RHEL 10 *Managing file systems* → ACLs; `man setfacl`.
