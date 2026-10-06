#!/usr/bin/env bash
d="/srv/$P_WORD-inbox"; mkdir -p "$d/old"
for i in 1 2 3 4 5; do echo "id,value\n$i,$((i*7))" > "$d/export-$i.csv"; done
for i in 1 2 3; do echo tmp > "$d/scratch-$i.tmp"; done
echo "inbox for $P_WORD" > "$d/README"; echo "keep me" > "$d/notes.txt"
