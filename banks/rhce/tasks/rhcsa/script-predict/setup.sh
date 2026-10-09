#!/usr/bin/env bash
install -d -o student -g student /home/student/scripts /home/student/answers
script='#!/bin/bash
# tally.sh N... - summarise a list of whole numbers
total=0
odd=0
for n in "$@"; do
  if (( n % 2 == 0 )); then
    total=$(( total + n ))
  else
    odd=$(( odd + 1 ))
    echo "odd: $n"
  fi
done
echo "even sum: $total"
echo "odd count: $odd of $#"'
printf '%s\n' "$script" > /home/student/scripts/tally.sh
chown student:student /home/student/scripts/tally.sh; chmod 0755 /home/student/scripts/tally.sh
# A root-only copy the grader runs (the candidate's copy may be edited).
install -d -m 0700 /usr/local/libexec/autorelabel
printf '%s\n' "$script" > /usr/local/libexec/autorelabel/tally-reference.sh
chmod 0700 /usr/local/libexec/autorelabel/tally-reference.sh
