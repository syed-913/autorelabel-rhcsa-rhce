#!/usr/bin/env bash
install -d -m 0755 "/exports/$P_SHARE"
echo "This is the $P_SHARE share on the utility server." > "/exports/$P_SHARE/README.txt"
echo "/exports/$P_SHARE $LAB_NETWORK(ro,sync,root_squash)" > "/etc/exports.d/$P_SHARE.exports"
exportfs -ra
