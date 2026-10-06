## Flatpak: add a remote and install an application

```bash
dnf install -y flatpak
flatpak remote-add --if-not-exists {{remote}} {{lab.flatpak_repofile}}   # system-wide by default
flatpak remotes --show-details
flatpak remote-ls {{remote}}                       # Firefox, Thunderbird, Red Hat runtime
flatpak install -y {{remote}} org.mozilla.firefox  # pulls com.redhat.Platform too
flatpak list --app
```

The `.flatpakrepo` file contains the repository URL **and** its GPG key, so signatures are
verified without extra steps. Flatpak works system-wide by default when run as root;
`--user` would install into your home directory instead.

References: RHEL 10 documentation on Flatpak (installing applications, managing remotes);
`man flatpak-remote-add`, `man flatpak-install`.
