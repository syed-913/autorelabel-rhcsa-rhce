#!/usr/bin/env bash
helper="!f() { echo username=student; echo password=$AR_STUDENT_PASSWORD; }; f"
d=/home/student/git/ansible
runuser -u student -- mkdir -p /home/student/git
test -d "$d/.git" || as_student git -c credential.helper="$helper" clone -q "$LAB_GIT_URL" "$d"
as_student git config --global user.name "Lab Student"
as_student git config --global user.email student@lab.example.com
runuser -u student -- mkdir -p "$d/playbooks"
cat > "$d/playbooks/$P_NAME.yml" <<'YML'
---
- name: Connectivity check
  hosts: all
  tasks:
    - name: Ping
      ansible.builtin.ping:
YML
chown student:student "$d/playbooks/$P_NAME.yml"
as_student git -C "$d" add "playbooks/$P_NAME.yml"
as_student git -C "$d" commit -q -m "$P_MSG"
as_student git -C "$d" -c credential.helper="$helper" push -q origin main
