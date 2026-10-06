#!/usr/bin/env bash
# Baseline for exam nodes and RHCE managed/control nodes: a correctly working
# system. Individual task setup scripts then create each task's starting point
# (unconfigured or broken), after this baseline and its verification reboot.
# common.sh is prepended by the app.

step "Network configuration"
lab_dev="$(nic_by_mac "$AR_LAB_MAC")" || { echo "lab NIC with MAC $AR_LAB_MAC not found" >&2; exit 1; }
write_mgmt_config
write_lab_config "$lab_dev" "$lab_dev"
remove_box_connections "$lab_dev"
record_fact lab_nic "$lab_dev"

step "Identity"
hostnamectl set-hostname "$AR_FQDN"
cat > /etc/hosts <<'EOF'
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
EOF

step "Accounts"
echo "root:$AR_ROOT_PASSWORD" | chpasswd
# Same file Anaconda writes when "Allow root SSH login with password" is ticked.
echo "PermitRootLogin yes" > /etc/ssh/sshd_config.d/01-permitrootlogin.conf
chmod 0600 /etc/ssh/sshd_config.d/01-permitrootlogin.conf
passwd -l vagrant >/dev/null

step "Software sources"
# Exam nodes start with no repositories; candidates configure them.
rm -f /etc/yum.repos.d/*.repo
dnf clean all >/dev/null 2>&1 || true

step "Time"
# Unreachable default pool, as on a fresh install; time tasks configure chrony.
systemctl enable chronyd >/dev/null 2>&1 || true

step "Baseline marker"
record_fact role "$AR_ROLE"
record_fact baseline_done "$(date -u +%FT%TZ)"
