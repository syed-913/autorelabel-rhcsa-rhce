#!/usr/bin/env bash
# Common mistake: modes written as YAML integers (0750 becomes decimal 750 → wrong permissions).
student_write app-dirs.yml <<YML
---
- name: Application directories
  hosts: prod
  tasks:
    - ansible.builtin.group: {name: $P_GRP}
    - ansible.builtin.file:
        path: "{{ item.path }}"
        state: directory
        group: "{{ item.group | default('root') }}"
        mode: "{{ item.mode }}"
      loop:
        - { path: /srv/$P_APP, mode: 0755 }
        - { path: /srv/$P_APP/data, mode: 2770, group: $P_GRP }
        - { path: /srv/$P_APP/logs, mode: 0750, group: $P_GRP }
    - ansible.builtin.file:
        src: "{{ item.value }}"
        dest: "/srv/$P_APP/{{ item.key }}"
        state: link
      loop: "{{ {'current': '/srv/$P_APP/data', 'journal': '/srv/$P_APP/logs'} | dict2items }}"
YML
as_student ansible-playbook app-dirs.yml || true
