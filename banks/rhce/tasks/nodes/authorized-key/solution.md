## A user with a key, deployed by Ansible

```bash
ssh-keygen -t ed25519 -N '' -f ~/.ssh/{{user}}_key
```

```yaml
---
- name: Deploy user with key
  hosts: dev,test
  tasks:
    - ansible.builtin.user:
        name: {{user}}
    - ansible.posix.authorized_key:
        user: {{user}}                       # whose authorized_keys file
        key: "{{ lookup('ansible.builtin.file', '/home/student/.ssh/{{user}}_key.pub') }}"
```

`lookup('file', ...)` reads the file **on the control node**. Test: `ssh -i ~/.ssh/{{user}}_key {{user}}@node1.lab.example.com`.

References: `ansible-doc ansible.posix.authorized_key`.
