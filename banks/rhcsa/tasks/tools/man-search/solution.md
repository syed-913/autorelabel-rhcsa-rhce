## Search the manual

```bash
mandb                         # build/refresh the index (needed on a fresh system)
man -k {{keyword}} > /root/man-{{keyword}}.txt    # same as: apropos {{keyword}}
man man                       # lists the sections: 1 commands, 5 file formats, 8 admin commands
echo 5 > /root/man-section.txt
```

In the exam, `man -k`, `man -K` (full-text search) and `/usr/share/doc` are your references.

References: `man man`, `man apropos`, `man mandb`.
