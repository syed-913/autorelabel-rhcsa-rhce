## LVM with community.general

```yaml
---
- name: LVM storage
  hosts: test
  tasks:
    - community.general.parted:
        device: {{lab.node2.disk1}}
        number: 1
        state: present
        part_end: 1500MiB
        flags: [lvm]
    - community.general.lvg:
        vg: {{vg}}
        pvs: {{lab.node2.disk1}}1
    - community.general.lvol:
        vg: {{vg}}
        lv: {{lv}}
        size: {{size}}m                  # m = MiB; also 100%FREE, 50%VG, ...
    - community.general.filesystem:
        fstype: ext4
        dev: /dev/{{vg}}/{{lv}}
    - ansible.posix.mount:
        path: /mnt/{{lv}}
        src: /dev/{{vg}}/{{lv}}
        fstype: ext4
        state: mounted
```

References: `ansible-doc community.general.lvg`, `ansible-doc community.general.lvol`.
