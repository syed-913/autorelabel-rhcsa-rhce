#!/usr/bin/env bash
# Self-test stand-in for: rsync -av --delete /srv/<word>-site/ root@node2:/srv/<word>-site/
rm -rf "/srv/$P_WORD-site"; ar_gen_tree "/srv/$P_WORD-site" "$P_WORD"
