#!/usr/bin/env bash
install -d -m 0755 /exports/direct
echo "This is the direct share." > /exports/direct/README.txt
echo "/exports/direct $LAB_NETWORK(ro,sync)" > /etc/exports.d/direct.exports
exportfs -ra
