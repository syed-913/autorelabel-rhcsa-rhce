## Partition → file system → mount

```yaml
---
- name: Data partition
  hosts: dev
  tasks:
    - community.general.parted:
        device: {{lab.node1.disk1}}
        number: 1
        state: present
        part_end: {{size}}MiB              # from the start of the disk
    - community.general.filesystem:
        fstype: {{fs}}
        dev: {{lab.node1.disk1}}1
    - ansible.posix.mount:
        path: {{mnt}}
        src: {{lab.node1.disk1}}1         # or UUID=... from ansible_facts['devices']
        fstype: {{fs}}
        state: mounted                    # mount now AND write /etc/fstab
```

`state: present` only writes fstab; `state: ephemeral` only mounts.

References: `ansible-doc community.general.parted`, `ansible-doc ansible.posix.mount`.
