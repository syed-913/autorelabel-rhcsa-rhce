## Classify paths with test

```bash
#!/bin/bash
p="$1"
if   [ -L "$p" ]; then echo symlink        # check -L first: -d and -f follow links
elif [ -d "$p" ]; then echo directory
elif [ -f "$p" ]; then echo file
elif [ -e "$p" ]; then echo other
else echo missing; exit 1
fi
```

References: `man test`, `man bash` (CONDITIONAL EXPRESSIONS).
