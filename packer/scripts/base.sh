#!/usr/bin/env bash
# Base box configuration: serial console, memory diet, exam realism.
set -Eeuo pipefail
trap 'echo "base.sh failed at line $LINENO" >&2' ERR

echo "STEP: kernel and bootloader"
# No kdump reservation (saves ~192 MB per VM); serial + VGA consoles.
grubby --update-kernel=ALL --remove-args="crashkernel rhgb quiet" --args="console=tty0 console=ttyS0,115200n8"
sed -i \
  -e 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' \
  -e 's/^GRUB_TERMINAL_OUTPUT=.*/GRUB_TERMINAL="console serial"/' \
  /etc/default/grub
grep -q '^GRUB_TERMINAL=' /etc/default/grub || echo 'GRUB_TERMINAL="console serial"' >> /etc/default/grub
grep -q '^GRUB_SERIAL_COMMAND=' /etc/default/grub || \
  echo 'GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"' >> /etc/default/grub
grep -q '^GRUB_TIMEOUT_STYLE=' /etc/default/grub || echo 'GRUB_TIMEOUT_STYLE=menu' >> /etc/default/grub
sed -i 's/ crashkernel=[^" ]*//g; s/ rhgb//g; s/ quiet//g' /etc/default/grub
grub2-editenv - unset menu_auto_hide || true
grub2-mkconfig -o /boot/grub2/grub.cfg

echo "STEP: services"
systemctl disable --now kdump.service 2>/dev/null || true
systemctl disable --now rhsmcertd.service 2>/dev/null || true
systemctl mask --now dnf-makecache.timer 2>/dev/null || true
systemctl enable qemu-guest-agent.service 2>/dev/null || true
systemctl enable serial-getty@ttyS0.service

echo "STEP: no subscription, no repositories (candidates configure repos themselves)"
if [[ -f /etc/dnf/plugins/subscription-manager.conf ]]; then
  sed -i 's/^enabled=.*/enabled=0/' /etc/dnf/plugins/subscription-manager.conf
fi
if [[ -f /etc/dnf/plugins/product-id.conf ]]; then
  sed -i 's/^enabled=.*/enabled=0/' /etc/dnf/plugins/product-id.conf
fi
if command -v subscription-manager >/dev/null; then subscription-manager clean >/dev/null 2>&1 || true; fi
rm -f /etc/yum.repos.d/*.repo

echo "STEP: identity"
# The box version marker the doctor and grader can read
install -d /etc/autorelabel
cat > /etc/autorelabel/box-release <<EOF
box=autorelabel/rhel10
rhel=$(sed -n 's/.*release \([0-9.]*\).*/\1/p' /etc/redhat-release)
built=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
chmod 0644 /etc/autorelabel/box-release
