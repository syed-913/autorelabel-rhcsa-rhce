## archive, then fetch

```yaml
---
- name: Collect configuration archives
  hosts: test
  tasks:
    - name: Archive {{src.dir}}
      community.general.archive:
        path: {{src.dir}}
        dest: /root/config.{{fmt.ext}}
        format: {{fmt.name}}                 # the default is gz
    - name: Copy it to control
      ansible.builtin.fetch:
        src: /root/config.{{fmt.ext}}
        dest: "/home/student/ansible/collected/{{ inventory_hostname_short }}.{{fmt.ext}}"
        flat: true                           # without it: collected/<host>/root/config.{{fmt.ext}}
```

`fetch` copies from the managed nodes to the control node (the opposite of `copy`), and creates
the destination directory. Without `flat: true` it builds `dest/<inventory host>/<full source
path>`, so each host gets its own subdirectory.

Check on a node with `tar -tvf /root/config.{{fmt.ext}}` (GNU tar recognises the compression).

References: `ansible-doc community.general.archive`, `ansible-doc ansible.builtin.fetch`.
