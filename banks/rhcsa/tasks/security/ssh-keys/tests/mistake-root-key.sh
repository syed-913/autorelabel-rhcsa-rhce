#!/usr/bin/env bash
# Common mistake: generating and copying the key as root instead of as the user.
[ -f /root/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N '' -f /root/.ssh/id_ed25519
python3 - "$P_USER@$LAB_NODE2_IP" "$P_PASSWORD" <<'PY'
import os, pty, sys, time
pid, fd = pty.fork()
if pid == 0:
    os.execvp("ssh-copy-id", ["ssh-copy-id", "-o", "StrictHostKeyChecking=accept-new", sys.argv[1]])
buf = b""
end = time.time() + 60
while time.time() < end:
    try:
        d = os.read(fd, 1024)
    except OSError:
        break
    if not d:
        break
    buf += d
    if b"password:" in buf.lower():
        os.write(fd, sys.argv[2].encode() + b"\n")
        buf = b""
os.waitpid(pid, 0)
PY
