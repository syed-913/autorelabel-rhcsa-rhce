#!/usr/bin/env bash
# Self-test stand-in for "rsync -a node1:/opt/<word>-docs/ node2:/opt/<word>-docs/":
ar_gen_tree "/opt/$P_WORD-docs" "$P_WORD"
