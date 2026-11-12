#!/usr/bin/env bash
# The search is saved first; later in the exam another task installs software whose manual
# pages match the keyword too (here: one more page, indexed the way a package install does it).
mandb -q
man -k "$P_KEYWORD" > "/root/man-$P_KEYWORD.txt"
echo 5 > /root/man-section.txt
mkdir -p /usr/local/share/man/man8
printf '.TH LAB-EXTRA 8\n.SH NAME\nlab-extra \\- a later addition about %s handling\n' "$P_KEYWORD" \
  > /usr/local/share/man/man8/lab-extra.8
mandb -q
