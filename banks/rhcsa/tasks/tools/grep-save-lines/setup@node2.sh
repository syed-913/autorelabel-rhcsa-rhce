#!/usr/bin/env bash
mkdir -p /usr/share/doc/lab
python3 - "$P_WORD" > /usr/share/doc/lab/events.log <<'PY'
import random, sys
w = sys.argv[1]
words = ["backup", "timeout", "denied", "quota", "restart", "login", "sync"]
rnd = random.Random(w)
for i in range(400):
    a, b = rnd.choice(words), rnd.choice(words)
    if i % 37 == 0:
        a = w.upper()          # case variants must not match
    if i % 53 == 0:
        print("")
        continue
    print(f"2026-09-{(i % 28) + 1:02d} host{i % 5} job[{1000 + i}]: {a} event, {b} handled")
PY
