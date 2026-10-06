## Web content blocked by SELinux file contexts

Diagnose:

```bash
curl -I http://localhost/                    # 403
ls -Zd /srv/{{site}} /srv/{{site}}/index.html  # var_t (not httpd_sys_content_t)
ausearch -m AVC -ts recent | grep httpd      # denials for httpd_t reading var_t
```

Fix with a **policy rule** plus a relabel:

```bash
semanage fcontext -a -t httpd_sys_content_t "/srv/{{site}}(/.*)?"
restorecon -Rv /srv/{{site}}
curl http://localhost/
```

`semanage fcontext -l -C` shows your local rules. An equivalence rule
(`semanage fcontext -a -e /var/www /srv/{{site}}`) is also correct.

**Classic mistakes:** `chcon -t httpd_sys_content_t` works now but is not a rule, so a relabel
(or `restorecon`) silently undoes it and new files get the wrong type. `setenforce 0` "fixes" it
by switching SELinux off, which the task forbids.

References: RHEL 10 *Using SELinux* (Apache in a non-standard configuration);
`man semanage-fcontext` (EXAMPLES section), `man httpd_selinux`.
