#!/usr/bin/env bash
grep -E "^${P_PREFIX}[^[:alnum:]].*[^0-9][0-9]{4}\$" /usr/share/doc/lab/app.log > "/root/$P_PREFIX-codes.txt"
