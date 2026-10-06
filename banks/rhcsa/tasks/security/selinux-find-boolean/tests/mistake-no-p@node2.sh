#!/usr/bin/env bash
setsebool "$P_CASE_BOOLEAN" on; echo "$P_CASE_BOOLEAN" > /root/boolean.txt
