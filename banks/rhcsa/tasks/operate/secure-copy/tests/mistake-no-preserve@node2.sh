#!/usr/bin/env bash
# Common mistake: copying without preserving modes and timestamps (scp -r / cp -r).
tmp="$(mktemp -d)"; ar_gen_tree "$tmp/d" "$P_WORD"
mkdir -p "/opt/$P_WORD-docs"; cp -r "$tmp/d/." "/opt/$P_WORD-docs/"
chmod -R u=rwX,go=rX "/opt/$P_WORD-docs"; touch "/opt/$P_WORD-docs"/* "/opt/$P_WORD-docs"/sub/*
rm -rf "$tmp"
