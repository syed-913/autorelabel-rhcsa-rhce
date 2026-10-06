## Configure software repositories

Create one `.repo` file on **each** node (here `/etc/yum.repos.d/lab.repo`):

```ini
[BaseOS]
name=RHEL 10 BaseOS
baseurl={{lab.repo_baseos}}
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release

[AppStream]
name=RHEL 10 AppStream
baseurl={{lab.repo_appstream}}
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
```

Then `dnf repolist` and `dnf makecache`. Copy the same file to node2, for example with
`scp /etc/yum.repos.d/lab.repo root@node2:/etc/yum.repos.d/`.

An equally valid way: `dnf config-manager --add-repo {{lab.repo_baseos}}` (once per URL) plus
`rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release`.

**Classic mistakes:** setting `gpgcheck=0` to silence key errors (the task requires signature
checking); using the top-level DVD URL instead of the `BaseOS`/`AppStream` directories; forgetting
node2 (later tasks there will fail because nothing can be installed).

References: RHEL 10 *Managing software with the DNF tool*; `man dnf.conf`.
