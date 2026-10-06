#!/usr/bin/env bash
ar_install rsync
tmp="$(mktemp -d)"; ar_gen_tree "$tmp/site" "$P_WORD"
install -d /etc/autorelabel; ar_tree_digest "$tmp/site" > "/etc/autorelabel/$P_WORD-site.digest"
rm -rf "$tmp"
mkdir -p "/srv/$P_WORD-site"; echo "outdated" > "/srv/$P_WORD-site/index.txt"
echo "remove me" > "/srv/$P_WORD-site/old-page.html"
