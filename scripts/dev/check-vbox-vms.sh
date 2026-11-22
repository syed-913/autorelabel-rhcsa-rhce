#!/usr/bin/env bash
# Compare the settings of a running RHCSA VirtualBox lab (made by autorelabel) with the ones Vagrant
# gave the same VMs in 1.4.2 (tests/fixtures/vagrant-virtualbox-rhcsa-*.txt). Read-only: it only
# runs VBoxManage showvminfo. What differs by nature (UUIDs, disk paths, the SSH port) is masked.
#
#   VBOX_USER_HOME=<lab storage>/autorelabel/virtualbox/profile scripts/dev/check-vbox-vms.sh
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
: "${VBOX_USER_HOME:?set VBOX_USER_HOME to the VirtualBox profile of autorelabel}"
rc=0
for vm in utility node1 node2; do
  ours="$(VBoxManage showvminfo "autorelabel-rhcsa-$vm" --machinereadable 2>&1 \
    | grep -vE '^(UUID|CfgFile|SnapFldr|LogFldr|hardwareuuid|VMStateChangeTime|CurrentSnapshot|SnapshotName|SnapshotUUID|SnapshotDescription|GuestOSType|GuestAdditions|VideoMode|SessionName)' \
    | grep -vE 'ImageUUID|^"SATA-[0-9]-0"=' \
    | sed -E 's#/home/[^"]*/#PATH/#g; s#"\{[0-9a-f-]+\}"#"UUID"#g; s#(Forwarding\([0-9]+\)="ssh,tcp,127.0.0.1,)[0-9]+#\1PORT#; s#/run/user/[0-9]+/#RUNTIME/#')"
  if diff <(cat "tests/fixtures/vagrant-virtualbox-rhcsa-$vm.txt") <(printf '%s\n' "$ours"); then
    echo "$vm: identical to the VM Vagrant made"
  else
    echo "$vm: DIFFERENT (< Vagrant, > now)"; rc=1
  fi
done
exit $rc
