## Fixing check-hosts.sh

Three bugs:

```bash
if [ $# -gt 1 ]; then        # ✗ "more than one argument"  →  [ $# -lt 1 ]  (or -eq 0)
...
  if getent hosts "$host" > /dev/null; then
    echo "$host down"        # ✗ inverted: success means the name resolves → "up"
...
done < "$2"                  # ✗ the file is the first argument → "$1"
```

Fixed version:

```bash
#!/bin/bash
if [ $# -lt 1 ]; then
  echo "usage: $0 FILE" >&2
  exit 2
fi
while read -r host; do
  if getent hosts "$host" > /dev/null; then
    echo "$host up"
  else
    echo "$host down"
  fi
done < "$1"
```

Test every branch: `./check-hosts.sh; echo $?`, then with a file of good and bad names.
`bash -n` checks syntax, `bash -x` traces execution.

References: `man bash` (Special Parameters, CONDITIONAL EXPRESSIONS); `man getent`.
