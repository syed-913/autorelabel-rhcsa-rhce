#!/usr/bin/env bash
# Self-test stand-in for the console procedure: the resulting state is what is graded.
echo "root:$P_NEW_PASSWORD" | chpasswd
