## rescue with the error message

```yaml
---
- name: Deploy the web servers
  hosts: dev,webservers
  tasks:
    - name: Web server
      block:
        - ansible.builtin.dnf: {name: httpd, state: present}
        - ansible.builtin.copy:
            content: "Welcome to {{ ansible_facts['hostname'] }}\n"
            dest: /var/www/html/index.html
        - ansible.builtin.service: {name: httpd, state: started, enabled: true}
      rescue:
        - ansible.builtin.copy:
            content: "{{ ansible_failed_result.msg }}\n"     # the failed task's result
            dest: /root/web-failed.txt
        - ansible.builtin.service: {name: httpd, state: stopped, enabled: false}
      always:
        - ansible.builtin.copy: {content: "attempted\n", dest: /root/web-attempted.txt}
```

Inside `rescue`, `ansible_failed_task` and `ansible_failed_result` describe what failed. The
service may already be enabled when the start fails, so the rescue turns it off explicitly.

References: Ansible docs *Blocks* (error handling).
