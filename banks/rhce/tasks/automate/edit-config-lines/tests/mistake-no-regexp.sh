#!/usr/bin/env bash
# Common mistake: lineinfile without regexp adds a second MaxAuthTries line.
student_write sshd-tune.yml <<YML
---
- name: Tune sshd
  hosts: prod
  tasks:
    - ansible.builtin.lineinfile: {path: /etc/ssh/sshd_config.d/50-lab.conf, line: MaxAuthTries $P_TRIES}
    - ansible.builtin.blockinfile:
        path: /etc/ssh/sshd_config.d/50-lab.conf
        block: |
          LoginGraceTime $P_GRACE
          ClientAliveInterval 300
YML
as_student ansible-playbook sshd-tune.yml
