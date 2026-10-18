## Find a boolean by description

```bash
semanage boolean -l | grep -iE 'samba|mail|db|nfs'      # name, state, default, description
setsebool -P <boolean> on
getsebool <boolean>
echo <boolean> > /root/boolean.txt
```

On RHEL 10 the descriptions are built from the names ("Allow httpd to can sendmail"), so search
for the service and a keyword of what it should do: `semanage boolean -l | grep -i samba | grep -i home`.

References: `man semanage-boolean`, `man setsebool`.
