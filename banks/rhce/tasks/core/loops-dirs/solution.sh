#!/usr/bin/env bash
student_write app-dirs.yml <<YML
---
- name: Application directories
  hosts: prod
  vars:
    app_dirs:
      - { path: /srv/$P_APP, mode: "0755" }
      - { path: /srv/$P_APP/data, mode: "2770", group: $P_GRP }
      - { path: /srv/$P_APP/logs, mode: "0750", group: $P_GRP }
    app_links:
      current: /srv/$P_APP/data
      journal: /srv/$P_APP/logs
  tasks:
    - name: Group
      ansible.builtin.group:
        name: $P_GRP
        state: present

    - name: Directories
      ansible.builtin.file:
        path: "{{ item.path }}"
        state: directory
        owner: root
        group: "{{ item.group | default('root') }}"
        mode: "{{ item.mode }}"
      loop: "{{ app_dirs }}"

    - name: Links
      ansible.builtin.file:
        src: "{{ item.value }}"
        dest: "/srv/$P_APP/{{ item.key }}"
        state: link
      loop: "{{ app_links | dict2items }}"
YML
as_student ansible-playbook app-dirs.yml
