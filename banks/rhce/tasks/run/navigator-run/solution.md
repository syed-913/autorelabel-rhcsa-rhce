## ansible-navigator run vs ansible-playbook

```bash
mkdir -p ~/ansible/artifacts
ansible-navigator run ee-run.yml -m stdout \
    --eei {{lab.ee_image}} --pp missing \
    --pae true --pas ~/ansible/artifacts/ee-run.json
ansible-playbook ee-run.yml          # second run: changed=0
```

The same in `ansible-navigator.yml`:

```yaml
ansible-navigator:
  execution-environment:
    image: {{lab.ee_image}}
    pull:
      policy: missing
  mode: stdout
  playbook-artifact:
    enable: true
    save-as: "{playbook_dir}/artifacts/{playbook_name}.json"
```

`ansible-navigator replay artifacts/ee-run.json` reopens a finished run.

References: `ansible-navigator run --help`; Ansible docs *ansible-navigator settings*.
