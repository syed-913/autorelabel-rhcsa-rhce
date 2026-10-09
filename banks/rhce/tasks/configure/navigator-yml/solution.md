## ansible-navigator.yml

```yaml
---
ansible-navigator:
  execution-environment:
    image: {{lab.ee_image}}
    pull:
      policy: {{policy}}          # missing: pull only if absent · never: never pull
  mode: stdout
  playbook-artifact:
    enable: false
```

Navigator looks for `ansible-navigator.yml` in the current directory (then `~/.ansible-navigator.yml`).
`ansible-navigator settings --sample` prints every key with comments; `ansible-navigator settings
--effective` shows what is in force. With the default policy (`tag`), the `:latest` tag makes
navigator try to pull from a registry that doesn't exist.

References: `ansible-navigator settings --sample`; Ansible docs *ansible-navigator settings*.
