#!/usr/bin/env bash
# Valid alternative: paths relative to the project directory.
cfg=/home/student/ansible/ansible.cfg
python3 - "$cfg" "$P_FORKS" "$P_TIMEOUT" <<'PY'
import configparser, sys
path, forks, timeout = sys.argv[1:]
cp = configparser.ConfigParser(interpolation=None)
cp.read(path)
d = cp["defaults"]
d["forks"] = forks
d["log_path"] = "ansible.log"
d["gathering"] = "smart"
d["fact_caching"] = "jsonfile"
d["fact_caching_connection"] = "facts_cache"
d["fact_caching_timeout"] = timeout
with open(path, "w") as f:
    cp.write(f)
PY
chown student:student "$cfg"
as_student ansible all -m ansible.builtin.setup -a 'filter=ansible_hostname' >/dev/null
