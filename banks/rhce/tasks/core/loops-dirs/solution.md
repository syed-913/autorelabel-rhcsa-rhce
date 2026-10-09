## Loops over a list and a dictionary

```yaml
---
- name: Application directories
  hosts: prod
  vars:
    app_dirs:
      - { path: /srv/{{app}}, mode: "0755" }
      - { path: /srv/{{app}}/data, mode: "2770", group: {{grp}} }
      - { path: /srv/{{app}}/logs, mode: "0750", group: {{grp}} }
    app_links:
      current: /srv/{{app}}/data
      journal: /srv/{{app}}/logs
  tasks:
    - ansible.builtin.group:
        name: {{grp}}
    - ansible.builtin.file:
        path: "{{ item.path }}"
        state: directory
        owner: root
        group: "{{ item.group | default('root') }}"   # optional key
        mode: "{{ item.mode }}"
      loop: "{{ app_dirs }}"
    - ansible.builtin.file:
        src: "{{ item.value }}"
        dest: "/srv/{{app}}/{{ item.key }}"
        state: link
      loop: "{{ app_links | dict2items }}"              # [{key: current, value: ...}, ...]
```

**Classic mistake:** unquoted modes. YAML reads `0750` as an octal *integer* in some contexts
and `2770` as decimal; always quote modes (`"0750"`).

References: Ansible docs *Loops*; `ansible-doc ansible.builtin.file`.
