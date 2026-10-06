## Loop over arguments

```bash
#!/bin/bash
for arg in "$@"; do          # "$@" keeps each argument intact, spaces included
    echo "$arg: ${#arg}"     # ${#var} = length
done
echo "total: $#"
```

**Classic mistake:** `for arg in $@` (unquoted) splits `'two words'` into two arguments.

References: `man bash` (`for`, `$@`, `${#parameter}`).
