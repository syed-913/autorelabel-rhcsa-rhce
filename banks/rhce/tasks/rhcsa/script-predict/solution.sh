#!/usr/bin/env bash
# shellcheck disable=SC2086
runuser -u student -- bash -c "/home/student/scripts/tally.sh $P_ARGS > /home/student/answers/tally.txt"
