## Roles from a requirements file

`roles/requirements.yml`:

```yaml
---
- src: {{lab.roles_url}}/lab_webserver.tar.gz
  name: webserver
- src: {{lab.roles_url}}/lab_balancer.tar.gz
  name: balancer
```

```bash
ansible-galaxy role install -r roles/requirements.yml -p roles
ansible-galaxy role list -p roles
```

`roles.yml`:

```yaml
---
- name: Web servers
  hosts: webservers
  roles:
    - role: webserver
      webserver_content: "Served by {{ ansible_facts['hostname'] }}"

- name: Load balancers
  hosts: balancers
  roles:
    - balancer
```

Order matters: the balancer's configuration template lists the web servers using their facts,
which exist once the first play has run against them.

References: Ansible docs *Galaxy User Guide* (requirements files).
