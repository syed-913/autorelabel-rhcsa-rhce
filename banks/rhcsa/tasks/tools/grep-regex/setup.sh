#!/usr/bin/env bash
mkdir -p /usr/share/doc/lab
python3 - > /usr/share/doc/lab/app.log <<'PY'
import random
rnd = random.Random(7)
prefixes = ["ERROR", "WARN", "FAIL", "INFO", "error", " ERROR", "ERRORS"]
for i in range(300):
    p = rnd.choice(prefixes)
    n = rnd.choice([rnd.randint(1000, 9999), rnd.randint(10, 999), rnd.randint(10000, 99999)])
    tail = rnd.choice([f"code {n}", f"code {n} retry", f"id={n}", f"code {n}"])
    print(f"{p} module{i % 7}: operation finished with {tail}")
PY
