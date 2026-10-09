## if / elif / else and for in a template

```jinja
Host: {{ ansible_facts['hostname'] }}
{% if 'dev' in group_names %}
Role: development
{% elif 'prod' in group_names %}
Role: production
{% else %}
Role: other
{% endif %}
{% for contact in lab_contacts %}
Contact: {{ contact }}
{% endfor %}
```

Ansible's template module sets `trim_blocks`, so a line holding only `{% ... %}` leaves no
empty line behind.

References: Jinja2 *Template Designer Documentation*; `ansible-doc ansible.builtin.template`.
