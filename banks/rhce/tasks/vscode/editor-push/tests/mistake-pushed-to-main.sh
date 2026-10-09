#!/usr/bin/env bash
# Common mistake: committed on main and pushed main (no branch).
helper="!f() { echo username=student; echo password=$AR_STUDENT_PASSWORD; }; f"
d=/home/student/git/ansible
runuser -u student -- mkdir -p /home/student/git
test -d "$d/.git" || as_student git -c credential.helper="$helper" clone -q "$LAB_GIT_URL" "$d"
as_student git config --global user.name "Lab Student"
as_student git config --global user.email student@lab.example.com
printf -- '---\n- hosts: all\n  tasks:\n    - ansible.builtin.service: {name: %s, state: started, enabled: true}\n' "$P_SVC" > "$d/$P_FEAT.yml"
chown student:student "$d/$P_FEAT.yml"
as_student git -C "$d" add "$P_FEAT.yml"
as_student git -C "$d" commit -q -m "Add $P_FEAT playbook"
as_student git -C "$d" -c credential.helper="$helper" push -q origin main
