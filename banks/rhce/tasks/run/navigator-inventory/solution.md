## Inventories for ansible-navigator

`inventory-{{zone}}.yml`:

```yaml
---
{{zone}}:
  hosts:
    node5.lab.example.com:        # the balancers hosts of your lab
  vars:
    zone: {{zone}}
```

`ansible-navigator.yml`:

```yaml
---
ansible-navigator:
  ansible:
    inventory:
      entries:
        - /home/student/ansible/inventory
        - /home/student/ansible/inventory-{{zone}}.yml
  mode: stdout
```

```bash
ansible-navigator inventory --graph > inventory-graph.txt      # uses the configured entries
ansible-navigator inventory --list --host node5.lab.example.com # variables of one host
```

(`ansible-navigator inventory -i inventory -i inventory-{{zone}}.yml --graph` works without settings.)

References: `ansible-navigator inventory --help`; Ansible docs *How to build your inventory*.
