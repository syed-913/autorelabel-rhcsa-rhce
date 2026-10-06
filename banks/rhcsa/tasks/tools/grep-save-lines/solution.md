## Extract matching lines

```bash
grep '{{word}}' /usr/share/doc/lab/events.log > /root/{{word}}-lines.txt
wc -l /root/{{word}}-lines.txt
```

grep keeps the original order and is case-sensitive by default (`-i` would also match
`{{word}}`-in-capitals lines, which the task excludes).

References: `man grep`.
