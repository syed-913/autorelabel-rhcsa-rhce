#!/usr/bin/env bash
for p in alpha beta gamma; do
  install -d -m 0755 "/exports/projects/$p"
  echo "This is project $p." > "/exports/projects/$p/README.txt"
done
echo "/exports/projects $LAB_NETWORK(rw,sync,root_squash)" > /etc/exports.d/projects.exports
exportfs -ra
