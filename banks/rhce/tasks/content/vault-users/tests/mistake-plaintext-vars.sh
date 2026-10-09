#!/usr/bin/env bash
# Common mistake: lock.yml left unencrypted, and everyone created everywhere.
printf '%s\n' "$P_VAULTPW" | student_write secret.txt 0600
printf 'pw_developer: Dev-%s\npw_manager: Mgr-%s\n' "$P_DEVPW" "$P_MGRPW" | student_write lock.yml
student_write users-vault.yml <<'YML'
---
- name: Everyone
  hosts: dev,test,prod
  vars_files: [user_list.yml, lock.yml]
  tasks:
    - ansible.builtin.group: {name: devops}
    - ansible.builtin.user:
        name: "{{ item.name }}"
        groups: devops
        password: "{{ pw_developer | password_hash('sha512') }}"
      loop: "{{ users }}"
YML
as_student ansible-playbook users-vault.yml
