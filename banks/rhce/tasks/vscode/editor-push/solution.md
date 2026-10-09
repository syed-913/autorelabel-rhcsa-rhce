## A feature branch from VS Code

1. **File → Open Folder** `~/git/ansible` (clone it first from the terminal or with the
   *Clone Repository* command).
2. Click the branch name in the status bar → **Create new branch…** → `feature/{{feat}}`.
3. Create `{{feat}}.yml`:

   ```yaml
   ---
   - name: Service baseline
     hosts: all
     tasks:
       - ansible.builtin.service:
           name: {{svc}}
           state: started
           enabled: true
   ```

4. **Source Control** view: stage (+), enter a message, **Commit**, then **Publish Branch**.

Terminal equivalent:

```bash
git switch -c feature/{{feat}}
git add {{feat}}.yml && git commit -m "Add {{feat}} playbook"
git push -u origin feature/{{feat}}
```

References: VS Code docs *Using Git source control*; `man git-push`.
