## block / rescue / always

```yaml
---
- name: Logical volumes
  hosts: all
  tasks:
    - name: Volume group missing
      ansible.builtin.debug:
        msg: Volume group does not exist
      when: "'research' not in ansible_facts['lvm']['vgs']"

    - name: Logical volume and file system
      when: "'research' in ansible_facts['lvm']['vgs']"   # applies to every task in the block
      block:
        - community.general.lvol:
            vg: research
            lv: data
            size: {{big}}m
      rescue:                                  # runs only if a block task failed
        - ansible.builtin.debug:
            msg: Could not create a logical volume of that size
        - community.general.lvol:
            vg: research
            lv: data
            size: {{small}}m
      always:                                  # runs either way
        - community.general.filesystem:
            fstype: ext4
            dev: /dev/research/data
```

A host whose failure is *rescued* counts as successful in the play recap (`rescued=1`).
`ansible_facts['lvm']` lists volume groups (and logical volumes) when LVM is installed.

References: Ansible docs *Blocks*; `ansible-doc community.general.lvol`.
