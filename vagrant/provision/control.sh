#!/usr/bin/env bash
# RHCE control node: ansible-core (DVD), ansible-navigator (wheels), git, podman,
# code-server with the Red Hat Ansible extension, and an execution-environment image
# built offline from the DVD's own packages. Content was copied to /var/tmp/ar-content
# by the app beforehand. common.sh is prepended.

C=/var/tmp/ar-content
IMAGE="utility.lab.example.com:5000/ee-autorelabel:latest"

step "Network configuration"
lab_dev="$(nic_by_mac "$AR_LAB_MAC")" || { echo "lab NIC with MAC $AR_LAB_MAC not found" >&2; exit 1; }
write_mgmt_config
write_lab_config "$lab_dev" "$lab_dev"
remove_box_connections "$lab_dev"
# Load only the new lab profile: a full reload would also apply the removal of the box's
# connection, which on VirtualBox is the one carrying this SSH session.
nmcli connection load "/etc/NetworkManager/system-connections/${lab_dev}.nmconnection"
nmcli connection up "$lab_dev" >/dev/null
# Until the reboot, the box's DHCP connection on the management NIC is still active. On
# VirtualBox it lists NAT's DNS proxy first, which answers "no such domain" for the lab domain,
# and the steps below need the utility server by name. Drop those DNS servers from the running
# configuration only (mgmt0, which ignores them anyway, replaces the profile at the reboot).
mgmt_dev="$(nic_by_mac "$AR_MGMT_MAC")" && nmcli device modify "$mgmt_dev" ipv4.ignore-auto-dns yes \
  ipv6.ignore-auto-dns yes >/dev/null
record_fact lab_nic "$lab_dev"
hostnamectl set-hostname "$AR_FQDN"

step "Accounts"
echo "root:$AR_ROOT_PASSWORD" | chpasswd
echo "PermitRootLogin yes" > /etc/ssh/sshd_config.d/01-permitrootlogin.conf
chmod 0600 /etc/ssh/sshd_config.d/01-permitrootlogin.conf
id student >/dev/null 2>&1 || useradd -G wheel -c "Exam candidate" student
echo "student:$AR_STUDENT_PASSWORD" | chpasswd
# A persistent user manager and /run/user/<uid> for rootless podman (execution environments),
# also when the candidate is not logged in (code-server, grading).
loginctl enable-linger student
passwd -l vagrant >/dev/null

step "Repositories and packages"
sed -i 's/^enabled=.*/enabled=0/' /etc/dnf/plugins/subscription-manager.conf /etc/dnf/plugins/product-id.conf 2>/dev/null || true
rm -f /etc/yum.repos.d/*.repo
cat > /etc/yum.repos.d/lab.repo <<EOF
[BaseOS]
name=RHEL 10 BaseOS
baseurl=http://utility.$AR_DOMAIN/rhel10/BaseOS
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release

[AppStream]
name=RHEL 10 AppStream
baseurl=http://utility.$AR_DOMAIN/rhel10/AppStream
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
EOF
# The lab network is configured now; make sure the utility server answers.
for _ in $(seq 1 30); do curl -fs -o /dev/null "http://utility.$AR_DOMAIN/rhel10/BaseOS/repodata/repomd.xml" && break; sleep 2; done
dnf -y -q install ansible-core rhel-system-roles git podman python3-pip vim-enhanced nano bash-completion \
    tar rsync tree >/dev/null

step "ansible-navigator"
if [[ ! -x /opt/ansible-navigator/bin/ansible-navigator ]]; then
  # System site packages: navigator (and ansible-lint) use the DVD's ansible-core, the same
  # ansible-playbook the candidate runs, instead of a second copy from PyPI.
  python3 -m venv --system-site-packages /opt/ansible-navigator
  /opt/ansible-navigator/bin/pip install -q --no-index --find-links "$C/wheels" ansible-navigator
fi
ln -sfn /opt/ansible-navigator/bin/ansible-navigator /usr/local/bin/ansible-navigator
ln -sfn /opt/ansible-navigator/bin/ansible-lint /usr/local/bin/ansible-lint

step "Execution environment image (built offline from the DVD)"
if ! sudo -u student -i podman image exists "$IMAGE" 2>/dev/null; then
  root=/var/tmp/ee-root
  rm -rf "$root"; mkdir -p "$root"
  # The image root has its own rpm database: import the key there too (see common.sh).
  rpm --root "$root" --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
  dnf -y -q --installroot="$root" --releasever=10 --setopt=install_weak_deps=False --nodocs \
      --setopt=reposdir=/etc/yum.repos.d install python3 python3-pip ansible-core git-core openssh-clients \
      sudo tar findutils rsync >/dev/null
  dnf --installroot="$root" clean all >/dev/null 2>&1 || true
  build=/var/tmp/ee-build; rm -rf "$build"; mkdir -p "$build"
  tar -C "$root" -cf "$build/rootfs.tar" .
  cp -r "$C/wheels" "$build/wheels"; cp -r "$C/collections" "$build/collections"
  cat > "$build/Containerfile" <<'EOF'
FROM scratch
ADD rootfs.tar /
COPY wheels /tmp/wheels
COPY collections /tmp/collections
RUN python3 -m pip install --no-index --find-links /tmp/wheels ansible-runner && \
    for c in /tmp/collections/*.tar.gz; do ansible-galaxy collection install -p /usr/share/ansible/collections "$c"; done && \
    rm -rf /tmp/wheels /tmp/collections && mkdir -p /runner && chmod 0777 /runner
ENV HOME=/runner
WORKDIR /runner
LABEL org.opencontainers.image.title="autorelabel execution environment (RHEL 10, ansible-core 2.16)"
EOF
  chown -R student: "$build"
  sudo -u student -i podman build -q -t "$IMAGE" "$build" >/dev/null
  rm -rf "$root" "$build"
fi

step "Collections and system roles for the candidate"
install -d -o student -g student /home/student/ansible

if [[ "${AR_CODE_SERVER:-yes}" == "yes" ]] && compgen -G "$C/code-server/code-server-*.rpm" >/dev/null; then
  step "code-server (VS Code in the browser) with the Red Hat Ansible extension"
  dnf -y -q install "$C"/code-server/code-server-*.rpm >/dev/null
  runuser -u student -- mkdir -p /home/student/.config/code-server
  # The app reaches it through an SSH tunnel on the host's 127.0.0.1 (a secure context for the
  # browser); the lab address works too, without clipboard and web views. No workspace-trust
  # prompt (Restricted Mode would disable the Ansible extension) and nothing phoning home.
  cat > /home/student/.config/code-server/config.yaml <<EOF
bind-addr: 0.0.0.0:8080
auth: password
password: $AR_STUDENT_PASSWORD
cert: false
disable-telemetry: true
disable-update-check: true
disable-workspace-trust: true
disable-getting-started-override: true
EOF
  chown student: /home/student/.config/code-server/config.yaml; chmod 0600 /home/student/.config/code-server/config.yaml
  # Editor defaults: no AI chat or Lightspeed (an exam), the system Python, no welcome page.
  # Playbooks anywhere count as Ansible files (the extension alone only recognises paths such
  # as playbooks/ or roles/), so completion, documentation and linting work for every task.
  # Created as student: install -d would leave the parent directories it creates to root.
  runuser -u student -- mkdir -p /home/student/.local/share/code-server/User
  cat > /home/student/.local/share/code-server/User/settings.json <<'EOF'
{
    "chat.disableAIFeatures": true,
    "ansible.lightspeed.enabled": false,
    "ansible.python.interpreterPath": "/usr/bin/python3",
    "python.defaultInterpreterPath": "/usr/bin/python3",
    "workbench.startupEditor": "none",
    "telemetry.telemetryLevel": "off",
    "extensions.autoCheckUpdates": false,
    "extensions.autoUpdate": false,
    "files.associations": {"*.yml": "ansible", "*.yaml": "ansible"}
}
EOF
  chown student: /home/student/.local/share/code-server/User/settings.json
  # Dependencies first (extensions.txt lists them in install order): offline, code-server can't
  # fetch a missing dependency, and the Ansible extension won't activate without them.
  while read -r v; do
    [[ -n "$v" ]] || continue
    sudo -u student -i code-server --install-extension "$C/code-server/$v" >/dev/null 2>&1 \
      || sudo -u student -i code-server --install-extension "$C/code-server/$v"
  done < "$C/code-server/extensions.txt"
  sudo -u student -i code-server --list-extensions | grep -qx redhat.ansible
  systemctl enable --now code-server@student >/dev/null
  firewall-cmd -q --permanent --add-port=8080/tcp; firewall-cmd -q --reload
fi

step "Baseline marker"
rm -rf "$C"
record_fact role control
record_fact baseline_done "$(date -u +%FT%TZ)"
