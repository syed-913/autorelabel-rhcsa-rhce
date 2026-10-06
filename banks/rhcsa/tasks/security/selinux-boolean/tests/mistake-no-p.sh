#!/usr/bin/env bash
# Common mistake: setsebool without -P only changes the running policy.
for b in $P_PAIR; do setsebool "$b" on; done
