#!/usr/bin/env bash
# Common mistake: removing the argument from one kernel only (here: the rescue entry keeps it).
grubby --update-kernel=DEFAULT --remove-args="enforcing=0"
setenforce 1
