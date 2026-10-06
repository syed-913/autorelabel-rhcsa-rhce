## autofs indirect map

```bash
dnf install -y autofs nfs-utils
echo '/projects /etc/auto.projects' > /etc/auto.master.d/projects.autofs
echo '* -rw,sync {{lab.nfs_server}}:/exports/projects/&' > /etc/auto.projects
systemctl enable --now autofs
ls /projects/alpha        # triggers the mount
mount | grep projects
```

In the map, `*` matches any key (the directory name) and `&` substitutes it. One line per project
(`alpha -rw {{lab.nfs_server}}:/exports/projects/alpha`) works too. `ls /projects` alone shows
nothing until you access a subdirectory; that's normal for indirect maps.

References: RHEL 10 *Configuring and using network file services* → autofs; `man auto.master`, `man 5 autofs`.
