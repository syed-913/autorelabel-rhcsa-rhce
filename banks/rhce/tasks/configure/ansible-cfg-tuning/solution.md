## More ansible.cfg settings

All of these belong in `[defaults]`:

```ini
[defaults]
# ... existing settings ...
forks = {{forks}}
log_path = /home/student/ansible/ansible.log
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /home/student/ansible/facts_cache
fact_caching_timeout = {{timeout}}
```

Find option names and their section with `ansible-config list | less` (search for `ini:`), or
generate a fully commented file with `ansible-config init --disabled -t all > /tmp/full.cfg`.
Verify with `ansible-config dump --only-changed`.

References: `ansible-config list`; Ansible docs *Ansible Configuration Settings*.
