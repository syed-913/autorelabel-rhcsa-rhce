#!/usr/bin/env bash
# Make sure each boolean starts in its default "off" state.
for b in $P_PAIR; do setsebool -P "$b" off; done
