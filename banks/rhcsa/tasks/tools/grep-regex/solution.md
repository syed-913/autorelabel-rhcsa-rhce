## Regular expressions with grep

```bash
grep -E '^{{prefix}}[^[:alnum:]].*[^0-9][0-9]{4}$' /usr/share/doc/lab/app.log > /root/{{prefix}}-codes.txt
```

- `^{{prefix}}` at the start; `[^[:alnum:]]` stops `{{prefix}}S` from matching
- `[^0-9][0-9]{4}$`: exactly four digits at the end (a 5-digit number does not match)

`man 7 regex` documents the syntax (`-E` = extended regular expressions).

References: `man grep`, `man 7 regex`.
