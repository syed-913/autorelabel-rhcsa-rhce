## A per-user Flatpak remote by URL

```bash
dnf install -y flatpak                 # as root
su - {{user}}
curl -o lab.gpg http://{{lab.utility_fqdn}}/flatpak/lab.gpg
flatpak remote-add --user --gpg-import=lab.gpg {{remote}} {{lab.flatpak_repo}}
flatpak remotes --user --show-details
flatpak remote-ls --user {{remote}}
```

A plain repository URL has no key in it (unlike a `.flatpakrepo` file), so import it with
`--gpg-import`. `--user` keeps the remote in `~/.local/share/flatpak`.

**Classic mistakes:** `--no-gpg-verify` (signatures not checked); running it as root, which
makes the remote system-wide.

References: RHEL 10 Flatpak documentation; `man flatpak-remote-add`.
