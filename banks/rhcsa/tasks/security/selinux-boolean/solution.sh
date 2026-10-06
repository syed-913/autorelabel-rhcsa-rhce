#!/usr/bin/env bash
for b in $P_PAIR; do setsebool -P "$b" on; done
