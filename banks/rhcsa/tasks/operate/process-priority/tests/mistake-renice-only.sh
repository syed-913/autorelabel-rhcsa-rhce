#!/usr/bin/env bash
# Common mistake: renice the running process only.
renice -n "$P_NICE" -p "$(systemctl show -p MainPID --value "$P_WORD-indexer.service")" >/dev/null
