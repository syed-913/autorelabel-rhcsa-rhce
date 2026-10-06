#!/usr/bin/env bash
# Common mistake: -i also matches upper-case variants that the task excludes.
grep -i -- "$P_WORD" /usr/share/doc/lab/events.log > "/root/$P_WORD-lines.txt"
