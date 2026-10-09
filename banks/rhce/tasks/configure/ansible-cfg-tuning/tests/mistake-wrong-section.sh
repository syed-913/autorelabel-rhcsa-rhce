#!/usr/bin/env bash
# Common mistake: fact caching options under a [fact_caching] section that doesn't exist.
cfg=/home/student/ansible/ansible.cfg
cat >> "$cfg" <<CFG

[fact_caching]
fact_caching = jsonfile
fact_caching_connection = /home/student/ansible/facts_cache
fact_caching_timeout = $P_TIMEOUT
CFG
sed -i "/^\[defaults\]/a forks = $P_FORKS\nlog_path = /home/student/ansible/ansible.log\ngathering = smart" "$cfg"
as_student ansible all -m ansible.builtin.ping >/dev/null
