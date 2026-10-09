## Install collections into a project directory

```bash
cd ~/ansible
ansible-galaxy collection install {{lab.collections_url}}/ansible-posix.tar.gz -p ~/ansible/mycollections
ansible-galaxy collection install {{lab.collections_url}}/community-general.tar.gz -p ~/ansible/mycollections
ansible-galaxy collection list                 # both listed under ~/ansible/mycollections
ansible-doc ansible.posix.firewalld | head     # modules are found
```

Or with a requirements file:

```yaml
# collections/requirements.yml
collections:
  - name: {{lab.collections_url}}/ansible-posix.tar.gz
    type: url
  - name: {{lab.collections_url}}/community-general.tar.gz
    type: url
```

```bash
ansible-galaxy collection install -r collections/requirements.yml -p ~/ansible/mycollections
```

With `collections_path = /home/student/ansible/mycollections` in `ansible.cfg`, `-p` can even be
omitted: ansible-galaxy installs into the first configured path.

**Classic mistake:** installing into `~/.ansible/collections` (the default without a configured
path), then wondering why `ansible-navigator` / graders don't find the collection where asked.

References: Ansible docs *Using collections*; `ansible-galaxy collection install --help`.
