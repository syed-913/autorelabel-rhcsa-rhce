## Install a package from a local file

```bash
curl -O http://{{lab.utility_fqdn}}/rpms/labtools-1.0-1.el10.noarch.rpm
dnf install -y ./labtools-1.0-1.el10.noarch.rpm     # resolves dependencies from your repos
rpm -qi labtools
```

`rpm -ivh file.rpm` also works but does not resolve dependencies. Note `dnf install <URL>` also
accepts a URL directly.

References: RHEL 10 *Managing software with the DNF tool*; `man dnf`.
