## Switch user

```bash
su - {{user}}               # "-" gives a full login environment (home dir, PATH...)
vim ~/{{word}}.txt
exit
ls -l /home/{{user}}/{{word}}.txt
```

As root you could also `chown {{user}}: <file>` afterwards, but working as the user is the point.

References: `man su`.
