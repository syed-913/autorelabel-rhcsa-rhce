## Find a boolean by description

```bash
semanage boolean -l | grep -iE 'ftp|mail|database|nfs'      # name, state, default, description
setsebool -P <boolean> on
getsebool <boolean>
echo <boolean> > /root/boolean.txt
```

References: `man semanage-boolean`, `man setsebool`.
