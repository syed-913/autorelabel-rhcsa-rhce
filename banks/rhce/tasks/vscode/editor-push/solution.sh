#!/usr/bin/env bash
# Stand-in for the editor's Source Control actions (create branch, commit, publish).
helper="!f() { echo username=student; echo password=$AR_STUDENT_PASSWORD; }; f"
d=/home/student/git/ansible
runuser -u student -- mkdir -p /home/student/git
test -d "$d/.git" || as_student git -c credential.helper="$helper" clone -q "$LAB_GIT_URL" "$d"
as_student git config --global user.name "Lab Student"
as_student git config --global user.email student@lab.example.com
as_student git -C "$d" switch -q -c "feature/$P_FEAT"
cat > "$d/$P_FEAT.yml" <<YML
---
- name: Service baseline
  hosts: all
  tasks:
    - name: $P_SVC running and enabled
      ansible.builtin.service:
        name: $P_SVC
        state: started
        enabled: true
YML
chown student:student "$d/$P_FEAT.yml"
as_student git -C "$d" add "$P_FEAT.yml"
as_student git -C "$d" commit -q -m "Add $P_FEAT playbook"
as_student git -C "$d" -c credential.helper="$helper" push -q -u origin "feature/$P_FEAT"
as_student git -C "$d" switch -q main
