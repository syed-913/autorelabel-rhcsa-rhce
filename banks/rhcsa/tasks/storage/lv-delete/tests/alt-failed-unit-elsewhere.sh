#!/usr/bin/env bash
# Something unrelated fails at every boot (another task's service, say): systemd then reports
# the system as "degraded", which is still a normal boot.
umount /scratch
sed -i '\|[[:space:]]/scratch[[:space:]]|d' /etc/fstab
systemctl daemon-reload
lvremove -q -y "$P_VG/scratch"
cat > /etc/systemd/system/lab-unrelated.service <<'UNIT'
[Unit]
Description=An unrelated service that fails
[Service]
Type=oneshot
ExecStart=/usr/bin/false
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload; systemctl enable lab-unrelated.service
