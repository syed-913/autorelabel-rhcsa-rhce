## An apache role

```bash
cd ~/ansible
ansible-galaxy role init --init-path roles apache       # skeleton
```

`roles/apache/tasks/main.yml`:

```yaml
---
- ansible.builtin.dnf:
    name: [httpd, firewalld]
- ansible.builtin.service:
    name: "{{ item }}"
    state: started
    enabled: true
  loop: [httpd, firewalld]
- ansible.posix.firewalld:
    service: http
    permanent: true
    immediate: true
    state: enabled
- ansible.builtin.template:
    src: index.html.j2                 # found in roles/apache/templates/
    dest: /var/www/html/index.html
```

`roles/apache/templates/index.html.j2`:

```jinja
Welcome to {{ ansible_facts['fqdn'] }} on {{ ansible_facts['default_ipv4']['address'] }}
```

`apache.yml`:

```yaml
---
- name: Web servers
  hosts: webservers
  roles:
    - apache
```

Facts to know: `fqdn`, `hostname`, `default_ipv4.address` (the interface with the default route).

References: Ansible docs *Roles*; `ansible-doc ansible.builtin.template`.
