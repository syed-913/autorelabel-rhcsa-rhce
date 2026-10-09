## archive and unarchive

```yaml
---
- name: Back up sysconfig
  hosts: prod
  tasks:
    - community.general.archive:
        path: /etc/sysconfig
        dest: /root/sysconfig.tar.gz
        format: gz                   # the default; bz2, xz, zip and tar also exist

- name: Deploy the site
  hosts: dev
  tasks:
    - ansible.builtin.file:
        path: /srv/site
        state: directory
    - ansible.builtin.unarchive:
        src: http://{{lab.utility_fqdn}}/ansible/files/site-{{word}}.tar.gz
        dest: /srv/site               # must exist
        remote_src: true              # the managed node fetches the URL itself
```

Without `remote_src`, `unarchive` copies `src` from the control node first.

References: `ansible-doc community.general.archive`, `ansible-doc ansible.builtin.unarchive`.
