#!/usr/bin/env bash
# Common mistake: no ^ anchor (also matches " ERROR" and "ERRORS" lines) and no digit limit.
grep -E "$P_PREFIX.*[0-9]+\$" /usr/share/doc/lab/app.log > "/root/$P_PREFIX-codes.txt"
