#!/usr/bin/env bash
# Valid alternative: semanage boolean (also persistent).
for b in $P_PAIR; do semanage boolean -m --on "$b"; done
