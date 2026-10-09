## Configure Ansible on the control node

Work as `{{lab.control_user}}` in `{{lab.project_dir}}`.

`inventory` (INI format; a YAML inventory works just as well):

```ini
[dev]
node1.lab.example.com

[test]
node2.lab.example.com

[prod]
node3.lab.example.com      # (and node4 in the standard lab)

[balancers]
node5.lab.example.com      # (node2 in the lite lab)

[webservers:children]
prod
```

`ansible.cfg`:

```ini
[defaults]
inventory = /home/student/ansible/inventory
remote_user = ansible
roles_path = /home/student/ansible/roles:/usr/share/ansible/roles
collections_path = /home/student/ansible/mycollections
host_key_checking = False

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False
```

```bash
mkdir -p ~/ansible/roles ~/ansible/mycollections
ansible-inventory --graph              # verify the groups
ansible-config dump --only-changed     # verify every setting you changed
```

**Classic mistakes:** listing the prod hosts under `[webservers]` instead of `[webservers:children]`;
setting `roles_path` to the project directory only, so `rhel-system-roles.*` are no longer found;
putting the file in `~/.ansible.cfg`, which is ignored as soon as an `ansible.cfg` exists in the
current directory (`ANSIBLE_CONFIG` → `./ansible.cfg` → `~/.ansible.cfg` → `/etc/ansible/ansible.cfg`).

References: Ansible docs *How to build your inventory*, *Ansible Configuration Settings*;
`ansible-config init --disabled` prints every option with comments.
