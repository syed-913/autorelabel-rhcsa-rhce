## Hardware report from facts

```yaml
---
- name: Hardware report
  hosts: all
  tasks:
    - name: Download the empty report
      ansible.builtin.get_url:
        url: http://{{lab.utility_fqdn}}/ansible/files/hwreport.empty
        dest: /root/hwreport.txt
        force: true

    - name: Fill in the values
      ansible.builtin.lineinfile:
        path: /root/hwreport.txt
        regexp: "^{{ item.key }}="
        line: "{{ item.key }}={{ item.value }}"
      loop:
        - { key: HOST, value: "{{ inventory_hostname }}" }
        - { key: MEMORY, value: "{{ ansible_facts['memtotal_mb'] }}" }
        - { key: BIOS, value: "{{ ansible_facts['bios_version'] }}" }
        - { key: DISK_A_SIZE, value: "{{ ansible_facts['devices']['{{lab.disk_a}}']['size'] | default('NONE') }}" }
        - { key: DISK_B_SIZE, value: "{{ ansible_facts['devices']['{{lab.disk_b}}']['size'] | default('NONE') }}" }
        - { key: DISK_C_SIZE, value: "{{ ansible_facts['devices']['{{lab.disk_c}}']['size'] | default('NONE') }}" }
```

Find fact names with `ansible node1.lab.example.com -m ansible.builtin.setup -a 'filter=*mem*'`
(and `filter=ansible_devices`). `| default('NONE')` covers a disk that isn't there.

**Classic mistakes:** `memfree_mb` instead of `memtotal_mb`; no fallback, so the play fails on
the missing disk; `get_url` without `force: true` keeps an already edited file on reruns.

References: `ansible-doc ansible.builtin.lineinfile`, `ansible-doc ansible.builtin.get_url`.
