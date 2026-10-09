#!/usr/bin/env bash
# Common mistake: the command line copied into the answer file as well.
# shellcheck disable=SC2086
runuser -u student -- bash -c "{ echo '\$ tally.sh $P_ARGS'; /home/student/scripts/tally.sh $P_ARGS; } > /home/student/answers/tally.txt"
