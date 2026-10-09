#!/usr/bin/env bash
# Shared helpers, prepended to every provisioning script by the app.
# Inputs arrive as AR_* environment variables.
set -Eeuo pipefail
trap 'echo "ERROR: provisioning failed at line $LINENO: $BASH_COMMAND" >&2' ERR
export LC_ALL=C

step() { echo "STEP: $*"; }

nic_by_mac() {
  local want="${1,,}" dev
  for dev in /sys/class/net/*; do
    [[ -f "$dev/address" ]] || continue
    if [[ "$(cat "$dev/address")" == "$want" ]]; then basename "$dev"; return 0; fi
  done
  return 1
}

# Management NIC: renamed to mgmt0 (from the next boot), DHCP with a fixed
# reservation, never the default route, no DNS, trusted zone. Candidates are
# told not to touch it; it is how the grader reaches the VM.
write_mgmt_config() {
  local mac="${AR_MGMT_MAC,,}"
  install -d -m 0755 /etc/systemd/network
  cat > /etc/systemd/network/10-autorelabel-mgmt0.link <<EOF
# autorelabel: grader/management interface. Do not modify.
[Match]
MACAddress=$mac

[Link]
Name=mgmt0
EOF
  cat > /etc/NetworkManager/system-connections/mgmt0.nmconnection <<EOF
# autorelabel: grader/management connection. Do not modify.
[connection]
id=mgmt0
type=ethernet
interface-name=mgmt0
autoconnect=true
autoconnect-priority=100
zone=trusted

[ethernet]
mac-address=$mac

[ipv4]
method=auto
ignore-auto-dns=true
never-default=true
dhcp-send-hostname=false

[ipv6]
method=disabled
EOF
  chmod 0600 /etc/NetworkManager/system-connections/mgmt0.nmconnection
}

# Lab NIC: a static, persistent keyfile named after the interface (as the
# installer would name it). Arguments: <connection-name> <device>
write_lab_config() {
  local con="$1" dev="$2" mac="${AR_LAB_MAC,,}"
  cat > "/etc/NetworkManager/system-connections/${con}.nmconnection" <<EOF
[connection]
id=$con
type=ethernet
interface-name=$dev
autoconnect=true

[ethernet]
mac-address=$mac

[ipv4]
method=manual
address1=$AR_LAB_IP/$AR_LAB_PREFIX,$AR_GATEWAY
dns=$AR_DNS;
dns-search=$AR_DOMAIN;

[ipv6]
method=manual
address1=$AR_IPV6/64
addr-gen-mode=default
EOF
  chmod 0600 "/etc/NetworkManager/system-connections/${con}.nmconnection"
}

# Remove the box's installer connections. Takes effect at the next boot: never run
# `nmcli connection reload` afterwards (on VirtualBox the box's profile is the active one
# carrying the provisioning SSH session); load new profiles with `nmcli connection load`.
remove_box_connections() {
  local f
  for f in /etc/NetworkManager/system-connections/*.nmconnection; do
    [[ -e "$f" ]] || continue
    case "$(basename "$f")" in
      mgmt0.nmconnection|"$1.nmconnection") ;;
      *) rm -f "$f" ;;
    esac
  done
}

record_fact() {  # record_fact key value  -> /etc/autorelabel/facts (read back by the app)
  install -d -m 0755 /etc/autorelabel
  touch /etc/autorelabel/facts
  sed -i "/^$1=/d" /etc/autorelabel/facts
  echo "$1=$2" >> /etc/autorelabel/facts
}
