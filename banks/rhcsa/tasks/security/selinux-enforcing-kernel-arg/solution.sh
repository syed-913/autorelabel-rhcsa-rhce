#!/usr/bin/env bash
grubby --update-kernel=ALL --remove-args="enforcing=0"
setenforce 1
