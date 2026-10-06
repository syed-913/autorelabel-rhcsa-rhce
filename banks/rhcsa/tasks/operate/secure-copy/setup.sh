#!/usr/bin/env bash
ar_install rsync
ar_gen_tree "/opt/$P_WORD-docs" "$P_WORD"
# expected digest of the archive that lives on node2 (generated identically there)
tmp="$(mktemp -d)"; ar_gen_tar "$tmp/x.tar" "$P_WORD"
install -d /etc/autorelabel
sha256sum "$tmp/x.tar" | cut -d' ' -f1 > "/etc/autorelabel/$P_WORD-config.sha256"
rm -rf "$tmp"
