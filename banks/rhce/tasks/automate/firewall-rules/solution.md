## firewalld with Ansible

```yaml
---
- name: Firewall
  hosts: dev
  tasks:
    - ansible.builtin.service: {name: firewalld, state: started, enabled: true}
    - ansible.posix.firewalld:
        service: {{svc}}
        permanent: true            # saved configuration
        immediate: true            # and the running firewall
        state: enabled
    - ansible.posix.firewalld:
        port: {{port}}/tcp
        permanent: true
        immediate: true
        state: enabled
    - ansible.posix.firewalld:
        rich_rule: 'rule family="ipv4" source address="{{lab.utility.ip}}" port port="{{rport}}" protocol="tcp" accept'
        permanent: true
        immediate: true
        state: enabled
```

With only `permanent: true` the change waits for a reload; with only `immediate: true` it is
gone after a reboot.

References: `ansible-doc ansible.posix.firewalld`; `man firewalld.richlanguage`.
