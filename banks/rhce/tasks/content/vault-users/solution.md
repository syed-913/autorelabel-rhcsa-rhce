## Ansible Vault

```bash
cd ~/ansible
echo '{{vaultpw}}' > secret.txt && chmod 0600 secret.txt
ansible-vault create --vault-password-file secret.txt lock.yml
#   pw_developer: Dev-{{devpw}}
#   pw_manager: Mgr-{{mgrpw}}
ansible-vault view --vault-password-file secret.txt lock.yml    # check
```

`ansible.cfg`, `[defaults]`:

```ini
vault_password_file = /home/student/ansible/secret.txt
```

`users-vault.yml`:

```yaml
---
- name: Developers
  hosts: dev,test
  vars_files: [user_list.yml, lock.yml]
  tasks:
    - ansible.builtin.group: {name: devops}
    - ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: devops
        append: true
        password: "{{ pw_developer | password_hash('sha512') }}"
      loop: "{{ users | selectattr('job', 'equalto', 'developer') | list }}"

- name: Managers
  hosts: prod
  vars_files: [user_list.yml, lock.yml]
  tasks:
    - ansible.builtin.group: {name: opsmgr}
    - ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: opsmgr
        append: true
        password: "{{ pw_manager | password_hash('sha512') }}"
      loop: "{{ users | selectattr('job', 'equalto', 'manager') | list }}"
```

(`loop: "{{ users }}"` with `when: item.job == 'developer'` works as well.)

References: Ansible docs *Protecting sensitive data with Ansible vault*; `ansible-vault --help`.
