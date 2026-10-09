## SELinux modules

```yaml
---
- name: SELinux settings
  hosts: test
  tasks:
    - ansible.posix.selinux: {policy: targeted, state: enforcing}
    - ansible.posix.seboolean:
        name: {{bool}}
        state: true
        persistent: true                 # setsebool -P
    - ansible.builtin.file: {path: {{dir}}, state: directory, mode: "0755"}
    - community.general.sefcontext:      # semanage fcontext -a
        target: "{{dir}}(/.*)?"
        setype: public_content_t
    - ansible.builtin.command: restorecon -Rv {{dir}}
      register: restore
      changed_when: restore.stdout | length > 0
    - community.general.seport:          # semanage port -a
        ports: "{{port}}"
        proto: tcp
        setype: ssh_port_t
```

`sefcontext` only writes the rule into the policy; existing files keep their label until
`restorecon` runs.

References: the four modules' `ansible-doc` pages.
