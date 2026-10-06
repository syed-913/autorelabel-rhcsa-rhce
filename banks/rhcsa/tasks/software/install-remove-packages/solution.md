## Install and remove packages

```bash
dnf install -y {{pkgs}}
dnf remove -y {{remove}}
rpm -q {{pkgs}} {{remove}}
```

`dnf provides <file>` finds the package that ships a command, e.g. `dnf provides '*/semanage'`.

References: RHEL 10 *Managing software with the DNF tool*; `man dnf`.
