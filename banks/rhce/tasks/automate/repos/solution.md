## Repositories with ansible.builtin.yum_repository

`~/ansible/repos.yml`:

```yaml
---
- name: Configure the lab repositories
  hosts: all
  tasks:
    - name: BaseOS repository
      ansible.builtin.yum_repository:
        name: BaseOS                      # the repository ID: [BaseOS]
        description: RHEL 10 BaseOS       # the name= line
        baseurl: {{lab.repo_baseos}}
        gpgcheck: true
        gpgkey: {{lab.repo_gpgkey}}
        enabled: true

    - name: AppStream repository
      ansible.builtin.yum_repository:
        name: AppStream
        description: RHEL 10 AppStream
        baseurl: {{lab.repo_appstream}}
        gpgcheck: true
        gpgkey: {{lab.repo_gpgkey}}
        enabled: true
```

```bash
ansible-navigator run -m stdout repos.yml     # or: ansible-playbook repos.yml
ansible all -a 'dnf repolist'                  # both repositories on every node
```

**Classic mistakes:** `name:` vs `description:` swapped (the ID becomes "RHEL 10 BaseOS");
`gpgcheck: false` instead of providing the key; running against `localhost` only.

References: `ansible-doc ansible.builtin.yum_repository`; RHEL 10 *Managing software with DNF*.
