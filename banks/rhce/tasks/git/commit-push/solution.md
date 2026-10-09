## Clone, commit, push

```bash
mkdir -p ~/git && cd ~/git
git clone {{lab.git_url}}                       # user + password when asked
cd ansible
git config --global user.name "Lab Student"
git config --global user.email student@lab.example.com
mkdir -p playbooks
vim playbooks/{{name}}.yml
git add playbooks/{{name}}.yml
git commit -m "{{msg}}"
git push origin main                            # asks for the password again
git status                                       # "Your branch is up to date with 'origin/main'"
```

```yaml
---
- name: Connectivity check
  hosts: all
  tasks:
    - ansible.builtin.ping:
```

`git log origin/main..main` lists commits that were not pushed yet.

References: `man git-commit`, `man git-push`.
