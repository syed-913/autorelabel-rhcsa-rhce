#!/usr/bin/env bash
# Common mistake: "disabled" is not "permissive" (and needs a full relabel to undo).
sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
