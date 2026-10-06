## Static host name resolution

```bash
echo '{{lab.utility.ip}} {{alias}}.lab.example.com {{alias}}' >> /etc/hosts
getent hosts {{alias}}
```

Format: **address**, canonical name, then aliases. `/etc/nsswitch.conf` (`hosts: files dns ...`)
makes `/etc/hosts` win over DNS.

References: `man hosts`, `man nsswitch.conf`.
