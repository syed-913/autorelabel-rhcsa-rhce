#!/usr/bin/env bash
tmp="$(mktemp -d)"; ar_gen_tree "$tmp/site" "$P_WORD"
cp -a "$tmp/site/." "/srv/$P_WORD-site/"; rm -rf "$tmp"
