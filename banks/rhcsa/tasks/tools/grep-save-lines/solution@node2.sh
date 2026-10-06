#!/usr/bin/env bash
grep -- "$P_WORD" /usr/share/doc/lab/events.log > "/root/$P_WORD-lines.txt"
