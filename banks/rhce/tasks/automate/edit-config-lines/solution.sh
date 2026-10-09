#!/usr/bin/env bash
student_write sshd-tune.yml <<YML
---
- name: Tune sshd
  hosts: prod
  tasks:
    - name: MaxAuthTries
      ansible.builtin.lineinfile:
        path: /etc/ssh/sshd_config.d/50-lab.conf
        regexp: '^MaxAuthTries'
        line: MaxAuthTries $P_TRIES
        create: true
        mode: "0600"
      notify: Reload sshd
    - name: Timeouts
      ansible.builtin.blockinfile:
        path: /etc/ssh/sshd_config.d/50-lab.conf
        block: |
          LoginGraceTime $P_GRACE
          ClientAliveInterval 300
      notify: Reload sshd
  handlers:
    - name: Reload sshd
      ansible.builtin.service:
        name: sshd
        state: reloaded
YML
as_student ansible-playbook sshd-tune.yml
