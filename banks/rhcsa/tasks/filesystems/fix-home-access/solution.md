## A broken home directory

Check every layer:

```bash
ls -ld /home/{{user}}; ls -la /home/{{user}}     # owner root, mode 755
ls -Zd /home/{{user}}                            # tmp_t instead of user_home_dir_t
chown -R {{user}}:{{user}} /home/{{user}}
chmod 700 /home/{{user}}
restorecon -Rv /home/{{user}}
su - {{user}} -c 'touch ~/test && ls -l ~/test'
```

References: RHEL 10 *Managing file systems*; *Using SELinux* → restorecon.
