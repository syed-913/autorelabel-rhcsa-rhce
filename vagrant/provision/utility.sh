#!/usr/bin/env bash
# Utility server: plays Red Hat's classroom/utility host.
#   http://utility.lab.example.com/rhel10/{BaseOS,AppStream}  (from the attached DVD)
#   http://utility.lab.example.com/flatpak/                   (Red Hat Flatpaks from the DVD)
#   http://utility.lab.example.com/extras/                    (small extra repo for update tasks)
#   DNS for lab.example.com (dnsmasq), NTP server (chrony), NFS server.
# common.sh is prepended by the app. Idempotent: safe to re-run.

WEB=/var/www/html
ISO_MNT=$WEB/rhel10

step "Network configuration"
lab_dev="$(nic_by_mac "$AR_LAB_MAC")" || { echo "lab NIC with MAC $AR_LAB_MAC not found" >&2; exit 1; }
write_mgmt_config
write_lab_config "$lab_dev" "$lab_dev"
remove_box_connections "$lab_dev"
# Bring the lab NIC up now (the mgmt NIC, our SSH path, is left untouched until reboot).
# Load only the new lab profile: a full reload would also apply the removal of the box's
# connection, which on VirtualBox is the one carrying this SSH session.
nmcli connection load "/etc/NetworkManager/system-connections/${lab_dev}.nmconnection"
nmcli connection up "$lab_dev" >/dev/null
record_fact lab_nic "$lab_dev"
hostnamectl set-hostname "$AR_FQDN"
passwd -l vagrant >/dev/null

step "Mounting the RHEL 10 DVD"
install -d -m 0755 "$ISO_MNT"
if ! grep -q " $ISO_MNT " /etc/fstab; then
  echo "/dev/sr0  $ISO_MNT  iso9660  ro,nofail,context=system_u:object_r:httpd_sys_content_t:s0  0 0" >> /etc/fstab
fi
systemctl daemon-reload
mountpoint -q "$ISO_MNT" || mount "$ISO_MNT"
test -f "$ISO_MNT/BaseOS/repodata/repomd.xml" || { echo "DVD not readable at $ISO_MNT" >&2; exit 1; }

cat > /etc/yum.repos.d/rhel10-dvd.repo <<EOF
[dvd-BaseOS]
name=RHEL 10 BaseOS (DVD)
baseurl=file://$ISO_MNT/BaseOS
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release

[dvd-AppStream]
name=RHEL 10 AppStream (DVD)
baseurl=file://$ISO_MNT/AppStream
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
EOF

step "Installing services"
# Unregistered lab systems: silence the subscription-manager dnf plugin.
sed -i 's/^enabled=.*/enabled=0/' /etc/dnf/plugins/subscription-manager.conf /etc/dnf/plugins/product-id.conf 2>/dev/null || true
dnf -y -q install httpd dnsmasq nfs-utils chrony flatpak ostree createrepo_c rpm-build python3 >/dev/null
systemctl enable --now httpd >/dev/null

step "DNS for $AR_DOMAIN"
cat > /etc/dnsmasq.d/autorelabel.conf <<EOF
# autorelabel lab DNS
interface=$lab_dev
bind-dynamic
no-resolv
no-hosts
domain=$AR_DOMAIN
local=/$AR_DOMAIN/
EOF
IFS=';' read -ra hosts <<< "$AR_HOSTS"
for h in "${hosts[@]}"; do
  read -r ip ip6 fqdn short <<< "$h"
  echo "host-record=$fqdn,$short,$ip,$ip6" >> /etc/dnsmasq.d/autorelabel.conf
done
# Start once the lab address is up: dnsmasq listens on that interface only.
install -d -m 0755 /etc/systemd/system/dnsmasq.service.d
cat > /etc/systemd/system/dnsmasq.service.d/autorelabel.conf <<EOF
[Unit]
Wants=network-online.target
After=network-online.target
EOF
systemctl daemon-reload
systemctl enable --now dnsmasq >/dev/null
systemctl restart dnsmasq

step "Time server"
# Both address families: utility.lab.example.com resolves to IPv6 first, and chronyd keeps the
# first address of a name.
cat > /etc/chrony.conf <<EOF
# autorelabel lab time server
local stratum 8
allow $AR_LAB_NETWORK
allow $AR_LAB_NETWORK6
driftfile /var/lib/chrony/drift
makestep 1.0 3
rtcsync
logdir /var/log/chrony
EOF
systemctl enable --now chronyd >/dev/null
systemctl restart chronyd

step "NFS server"
install -d -m 0755 /exports /etc/exports.d
touch /etc/exports
systemctl enable --now nfs-server >/dev/null
exportfs -ra

step "Firewall"
for svc in http dns ntp nfs mountd rpc-bind; do
  firewall-cmd -q --permanent --add-service="$svc"
done
firewall-cmd -q --reload

step "Flatpak repository from the DVD (Red Hat Flatpaks)"
FP=$WEB/flatpak
REPO=$FP/repo
export GNUPGHOME=/root/.autorelabel-flatpak-gpg
if [[ ! -f "$REPO/summary" ]]; then
  install -d -m 0700 "$GNUPGHOME"
  if ! gpg --list-secret-keys --with-colons 2>/dev/null | grep -q '^sec'; then
    gpg --batch --pinentry-mode loopback --passphrase '' \
        --quick-gen-key 'Lab Flatpak Repository <flatpak@lab.example.com>' ed25519 sign never >/dev/null 2>&1
  fi
  KEYID="$(gpg --list-keys --with-colons | awk -F: '/^pub/ {print $5; exit}')"
  rm -rf "$REPO"
  install -d -m 0755 "$FP"
  ostree init --mode=archive-z2 --repo="$REPO"
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  # The DVD's OCI layout holds several images (runtime + apps); import each one.
  python3 - "$ISO_MNT/Flatpaks" "$work" <<'PY'
import json, os, sys
src, work = sys.argv[1], sys.argv[2]
index = json.load(open(os.path.join(src, "index.json")))
for n, m in enumerate(index["manifests"]):
    d = os.path.join(work, f"img{n}")
    os.makedirs(os.path.join(d, "blobs", "sha256"))
    digest = m["digest"].split(":", 1)[1]
    manifest = json.load(open(os.path.join(src, "blobs", "sha256", digest)))
    blobs = [digest, manifest["config"]["digest"].split(":", 1)[1]]
    blobs += [layer["digest"].split(":", 1)[1] for layer in manifest["layers"]]
    for b in blobs:
        os.symlink(os.path.join(src, "blobs", "sha256", b), os.path.join(d, "blobs", "sha256", b))
    with open(os.path.join(d, "oci-layout"), "w") as fh:
        json.dump({"imageLayoutVersion": "1.0.0"}, fh)
    # flatpak only picks an image from a layout whose manifest carries a ref name
    m = dict(m, annotations={"org.opencontainers.image.ref.name": "latest"})
    with open(os.path.join(d, "index.json"), "w") as fh:
        json.dump({"schemaVersion": 2, "manifests": [m]}, fh)
    print(d)
PY
  for img in "$work"/img*; do
    flatpak build-import-bundle --oci --gpg-sign="$KEYID" --gpg-homedir="$GNUPGHOME" "$REPO" "$img"
  done
  flatpak build-update-repo --gpg-sign="$KEYID" --gpg-homedir="$GNUPGHOME" \
      --title="Lab Flatpak Repository" "$REPO" >/dev/null
  rm -rf "$work"
  gpg --export "$KEYID" > "$FP/lab.gpg"
  key_b64="$(base64 -w0 "$FP/lab.gpg")"
  cat > "$FP/lab.flatpakrepo" <<EOF
[Flatpak Repo]
Title=Lab Flatpak Repository
Url=http://$AR_FQDN/flatpak/repo/
Homepage=http://$AR_FQDN/flatpak/
Comment=Red Hat Flatpaks served from the RHEL 10 DVD
GPGKey=$key_b64
EOF
  for app in org.mozilla.firefox:Firefox org.mozilla.Thunderbird:Thunderbird; do
    id="${app%%:*}"; title="${app##*:}"
    cat > "$FP/$id.flatpakref" <<EOF
[Flatpak Ref]
Name=$id
Branch=stable
Title=$title
Url=http://$AR_FQDN/flatpak/repo/
RuntimeRepo=http://$AR_FQDN/flatpak/lab.flatpakrepo
IsRuntime=false
GPGKey=$key_b64
EOF
  done
  restorecon -RF "$FP"
fi
flatpak remote-ls --system 2>/dev/null >/dev/null || true
ostree refs --repo="$REPO" 2>/dev/null | sed 's/^/  ref: /' || true

step "Extras repository (labtools 1.0 and 1.1)"
EX=$WEB/extras
if [[ ! -f "$EX/repodata/repomd.xml" ]]; then
  top="$(mktemp -d)"
  for ver in 1.0 1.1; do
    cat > "$top/labtools.spec" <<EOF
Name:      labtools
Version:   $ver
Release:   1%{?dist}
Summary:   Small helper used by lab exercises
License:   MIT
BuildArch: noarch

%description
Prints its own version. Used to practise installing and updating packages
from a remote repository or the local file system.

%install
mkdir -p %{buildroot}/usr/bin %{buildroot}/usr/share/doc/labtools
printf '#!/bin/sh\necho "labtools %{version}"\n' > %{buildroot}/usr/bin/labtools
chmod 0755 %{buildroot}/usr/bin/labtools
echo "labtools %{version}: lab exercise helper." > %{buildroot}/usr/share/doc/labtools/README

%files
/usr/bin/labtools
/usr/share/doc/labtools/README
EOF
    rpmbuild --quiet --define "_topdir $top" -bb "$top/labtools.spec" >/dev/null
  done
  install -d -m 0755 "$EX" "$WEB/rpms"
  find "$top/RPMS" -name '*.rpm' -exec cp {} "$EX/" \;
  cp "$EX"/labtools-1.0-*.rpm "$WEB/rpms/"
  createrepo_c -q "$EX"
  rm -rf "$top"
  restorecon -RF "$EX" "$WEB/rpms"
fi

step "Utility ready"
record_fact role utility
record_fact baseline_done "$(date -u +%FT%TZ)"
