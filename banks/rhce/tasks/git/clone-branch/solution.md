## git clone and switch

```bash
cd ~
git clone {{lab.git_content_url}}          # asks for user and password
cd lab-content
git branch -a                               # remotes/origin/release
git switch release                          # or: git checkout release
cat site/index.html                         # lab-content release 2.4
```

(`git clone -b release URL` clones and checks out the branch in one step.)

```yaml
---
- name: Deploy the released content
  hosts: dev
  tasks:
    - ansible.builtin.file:
        path: /srv/lab-content
        state: directory
    - ansible.builtin.copy:
        src: /home/student/lab-content/site/index.html
        dest: /srv/lab-content/index.html
```

References: `man git-clone`, `man git-switch`.
