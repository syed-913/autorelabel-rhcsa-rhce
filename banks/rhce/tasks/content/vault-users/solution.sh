#!/usr/bin/env bash
printf '%s\n' "$P_VAULTPW" | student_write secret.txt 0600
printf 'pw_developer: Dev-%s\npw_manager: Mgr-%s\n' "$P_DEVPW" "$P_MGRPW" | student_write lock.yml 0600
as_student ansible-vault encrypt --vault-password-file secret.txt lock.yml
python3 - <<'PY'
import configparser
p = "/home/student/ansible/ansible.cfg"
cp = configparser.ConfigParser(interpolation=None); cp.read(p)
cp["defaults"]["vault_password_file"] = "/home/student/ansible/secret.txt"
with open(p, "w") as f: cp.write(f)
PY
chown student:student /home/student/ansible/ansible.cfg
student_write users-vault.yml <<'YML'
---
- name: Developers
  hosts: dev,test
  vars_files:
    - user_list.yml
    - lock.yml
  tasks:
    - name: devops group
      ansible.builtin.group:
        name: devops
    - name: Developer accounts
      ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: devops
        append: true
        password: "{{ pw_developer | password_hash('sha512') }}"
      loop: "{{ users | selectattr('job', 'equalto', 'developer') | list }}"

- name: Managers
  hosts: prod
  vars_files:
    - user_list.yml
    - lock.yml
  tasks:
    - name: opsmgr group
      ansible.builtin.group:
        name: opsmgr
    - name: Manager accounts
      ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: opsmgr
        append: true
        password: "{{ pw_manager | password_hash('sha512') }}"
      loop: "{{ users | selectattr('job', 'equalto', 'manager') | list }}"
YML
as_student ansible-playbook users-vault.yml
