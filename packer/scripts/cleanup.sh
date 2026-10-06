#!/usr/bin/env bash
# Make the image clone-safe and small: unique IDs per VM, no host keys, no logs.
set -Eeuo pipefail
trap 'echo "cleanup.sh failed at line $LINENO" >&2' ERR

echo "STEP: cleanup"
dnf clean all >/dev/null 2>&1 || true
rm -rf /var/cache/dnf/* /var/tmp/* /tmp/* /root/anaconda-ks.cfg /root/original-ks.cfg
journalctl --rotate >/dev/null 2>&1 || true
journalctl --vacuum-time=1s >/dev/null 2>&1 || true
find /var/log -type f \( -name '*.log' -o -name 'messages' -o -name 'secure' -o -name 'cron' -o -name 'maillog' \) \
  -exec truncate -s 0 {} + 2>/dev/null || true

# Each clone must get its own machine-id and SSH host keys on first boot.
truncate -s 0 /etc/machine-id
rm -f /var/lib/systemd/random-seed
rm -f /etc/ssh/ssh_host_*
# NetworkManager: no stale DHCP leases or per-MAC connections
rm -f /var/lib/NetworkManager/*.lease /var/lib/NetworkManager/*.leases*
for f in /etc/NetworkManager/system-connections/*.nmconnection; do
  [[ -e "$f" ]] || continue
  if grep -q '^mac-address=' "$f"; then sed -i '/^mac-address=/d' "$f"; fi
done
history -c || true
rm -f /root/.bash_history /home/vagrant/.bash_history

echo "STEP: zero free space for compaction"
fstrim -av >/dev/null 2>&1 || true
sync
