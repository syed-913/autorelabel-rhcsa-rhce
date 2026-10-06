## Replace a Flatpak application

```bash
flatpak list --app
flatpak uninstall -y org.mozilla.firefox
flatpak install -y --from http://{{lab.utility_fqdn}}/flatpak/org.mozilla.Thunderbird.flatpakref
flatpak list --app
flatpak uninstall --unused     # optional: remove runtimes nothing uses anymore
```

A `.flatpakref` file describes one application (name, branch, repository URL, key). Installing
from it adds its origin remote automatically if needed.

References: RHEL 10 Flatpak documentation; `man flatpak-install`.
