## Process a file line by line

```bash
#!/bin/bash
while read -r host; do
    [[ -z "$host" || "$host" == \#* ]] && continue        # skip empty and comment lines
    addr="$(getent ahostsv4 "$host" | awk 'NR==1 {print $1}')"
    echo "$host ${addr:-unknown}"                          # default when empty
done < "$1"
```

`getent ahostsv4` uses the system resolver (/etc/hosts, then DNS), unlike `host`/`dig`.

References: `man bash` (`while`, `read`, `$( )`), `man getent`.
