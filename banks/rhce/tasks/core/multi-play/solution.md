## Two plays in one playbook

```yaml
---
- name: Web servers
  hosts: webservers
  tasks:
    - ansible.builtin.dnf: {name: httpd, state: present}
    - ansible.builtin.copy:
        content: "Served by {{ ansible_facts['hostname'] }}\n"
        dest: /var/www/html/index.html
    - ansible.builtin.service: {name: httpd, state: started, enabled: true}
    - ansible.posix.firewalld: {service: http, permanent: true, immediate: true, state: enabled}

- name: Check the web servers from the control node
  hosts: localhost              # implicit localhost: runs on control, connection local
  become: false                 # override become = True from ansible.cfg
  gather_facts: false
  tasks:
    - ansible.builtin.uri:
        url: "http://{{ item }}/"
        return_content: true
      loop: "{{ groups['webservers'] }}"
      register: pages
    - ansible.builtin.copy:
        content: "{{ pages.results | map(attribute='content') | join('') }}"
        dest: /home/student/ansible/web-check.txt
```

A registered variable in a loop holds `.results`, one entry per item.

**Classic mistakes:** forgetting `become: false` on localhost (needs sudo for the student, and
the file ends up owned by root); `permanent` without `immediate` (or the other way round).

References: `ansible-doc ansible.builtin.uri`, `ansible-doc ansible.posix.firewalld`.
