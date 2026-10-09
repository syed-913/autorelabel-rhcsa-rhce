## lineinfile, blockinfile and a handler

```yaml
---
- name: Tune sshd
  hosts: prod
  tasks:
    - ansible.builtin.lineinfile:
        path: /etc/ssh/sshd_config.d/50-lab.conf
        regexp: '^MaxAuthTries'         # the line to replace if it exists
        line: MaxAuthTries {{tries}}
        create: true
        mode: "0600"
      notify: Reload sshd
    - ansible.builtin.blockinfile:
        path: /etc/ssh/sshd_config.d/50-lab.conf
        block: |
          LoginGraceTime {{grace}}
          ClientAliveInterval 300
      notify: Reload sshd
  handlers:
    - name: Reload sshd
      ansible.builtin.service:
        name: sshd
        state: reloaded
```

Without `regexp`, `lineinfile` only checks whether the exact line exists and otherwise appends
it, so the old `MaxAuthTries 6` stays. Handlers run once, at the end of the play, and only if
a notifying task changed something. On sshd, the first value found wins: `sshd -T` shows what
is in force.

References: `ansible-doc ansible.builtin.lineinfile`; Ansible docs *Handlers*.
