## A report from command output

```bash
#!/bin/bash
echo "hostname=$(hostname)"
echo "kernel=$(uname -r)"
echo "selinux=$(getenforce)"
echo "users=$(wc -l < /etc/passwd)"     # "< file" so wc prints only the number
```

References: `man bash` (Command Substitution).
