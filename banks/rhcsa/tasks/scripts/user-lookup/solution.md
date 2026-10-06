## Arguments, tests and exit codes

```bash
#!/bin/bash
if [ $# -ne 1 ]; then
    echo "Usage: $(basename "$0") USERNAME" >&2      # >&2 = standard error
    exit 2
fi
if id "$1" >/dev/null 2>&1; then                     # branch on a command's exit status
    echo "$1 exists with UID $(id -u "$1")"
    exit 0
else
    echo "$1 not found"
    exit 1
fi
```

`chmod +x /usr/local/bin/{{name}}`, then test every case and check `echo $?`.

References: `man bash` (`$#`, `[ ]`/`test`, `exit`).
