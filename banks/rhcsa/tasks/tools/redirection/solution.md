## Redirection and pipes

```bash
lab-inventory > /root/inventory.out 2> /root/inventory.err   # stdout and stderr apart
lab-inventory --summary >> /root/inventory.out                # >> appends
lab-inventory --verbose &> /root/inventory.all                # both (= > file 2>&1)
lab-inventory 2>/dev/null | grep -c disk > /root/disk-count.txt
```

Order matters with `2>&1`: `cmd > file 2>&1` sends both to the file, while `cmd 2>&1 > file`
does not.

References: `man bash` → REDIRECTION.
