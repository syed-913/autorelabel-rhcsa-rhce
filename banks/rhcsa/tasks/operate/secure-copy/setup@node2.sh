#!/usr/bin/env bash
ar_install rsync
ar_gen_tar "/root/$P_WORD-config.tar" "$P_WORD"
# expected digest of node1's docs tree (generated identically here)
tmp="$(mktemp -d)"; ar_gen_tree "$tmp/docs" "$P_WORD"
install -d /etc/autorelabel
ar_tree_digest "$tmp/docs" > "/etc/autorelabel/$P_WORD-docs.digest"
rm -rf "$tmp"
