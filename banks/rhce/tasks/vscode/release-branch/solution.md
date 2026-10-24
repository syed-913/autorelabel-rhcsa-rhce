## A change on another branch, from VS Code

1. **Source Control** view → **Clone Repository** → `{{lab.git_content_url}}` → `~/git` (or
   `git clone` in the terminal), then open the folder.
2. Click the branch name in the status bar → choose **origin/release** (VS Code creates the local
   `release` branch tracking it).
3. Edit `site/index.html` to `lab-content release {{ver}}`, save.
4. Source Control: stage (+), message `Release {{ver}}`, **Commit**, then **Sync Changes** (push).

Terminal equivalent:

```bash
git switch release                       # creates release from origin/release
echo 'lab-content release {{ver}}' > site/index.html
git commit -am 'Release {{ver}}'
git push origin release
```

References: VS Code docs *Using Git source control*; `man git-switch`, `man git-push`.
