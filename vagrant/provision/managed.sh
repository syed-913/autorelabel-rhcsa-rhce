#!/usr/bin/env bash
# RHCE managed node: an 'ansible' account with a password (sudo with password via wheel),
# no repositories, nothing else. Candidates distribute keys and set up privilege
# escalation themselves. common.sh is prepended.

step "Network configuration"
lab_dev="$(nic_by_mac "$AR_LAB_MAC")" || { echo "lab NIC with MAC $AR_LAB_MAC not found" >&2; exit 1; }
write_mgmt_config
write_lab_config "$lab_dev" "$lab_dev"
remove_box_connections "$lab_dev"
record_fact lab_nic "$lab_dev"
hostnamectl set-hostname "$AR_FQDN"

step "Accounts"
echo "root:$AR_ROOT_PASSWORD" | chpasswd
echo "PermitRootLogin yes" > /etc/ssh/sshd_config.d/01-permitrootlogin.conf
chmod 0600 /etc/ssh/sshd_config.d/01-permitrootlogin.conf
id ansible >/dev/null 2>&1 || useradd -G wheel -c "Ansible automation" ansible
echo "ansible:$AR_ANSIBLE_PASSWORD" | chpasswd
passwd -l vagrant >/dev/null

step "Software sources"
sed -i 's/^enabled=.*/enabled=0/' /etc/dnf/plugins/subscription-manager.conf /etc/dnf/plugins/product-id.conf 2>/dev/null || true
rm -f /etc/yum.repos.d/*.repo
dnf clean all >/dev/null 2>&1 || true

step "Baseline marker"
record_fact role managed
record_fact baseline_done "$(date -u +%FT%TZ)"
