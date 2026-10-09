#!/usr/bin/env bash
# Common mistake: new password saved, but the file was never rekeyed.
printf '%s\n' "$P_NEW" | student_write salaries-pass.txt 0600
