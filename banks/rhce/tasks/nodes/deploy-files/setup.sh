#!/usr/bin/env bash
printf '# %s configuration\nlisten_port = 8080\nlog_level = info\nmax_workers = 4\n' "$P_APP" | student_write files/app.conf
