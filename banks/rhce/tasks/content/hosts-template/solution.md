## A template over all hosts

`templates/hosts.j2`:

```jinja
{% for host in groups['all'] %}
{{ hostvars[host]['ansible_facts']['default_ipv4']['address'] }} {{ hostvars[host]['ansible_facts']['fqdn'] }} {{ hostvars[host]['ansible_facts']['hostname'] }}
{% endfor %}
```

`hosts.yml`:

```yaml
---
- name: Gather facts from every host         # facts must exist for the whole loop
  hosts: all
  tasks: []

- name: Deploy /etc/myhosts
  hosts: dev
  tasks:
    - ansible.builtin.template:
        src: templates/hosts.j2
        dest: /etc/myhosts
        owner: root
        mode: "0644"
```

`hostvars[host]` gives another host's variables, but its facts only exist after a play
gathered them (or from a fact cache). A play with `hosts: dev` alone would leave the other
hosts' facts undefined.

References: Ansible docs *Templating (Jinja2)*, *Special variables*.
