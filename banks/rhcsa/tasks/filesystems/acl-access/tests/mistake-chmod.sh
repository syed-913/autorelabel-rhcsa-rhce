#!/usr/bin/env bash
# Common mistake: opening the base permissions to everyone instead of using ACLs.
chmod 0755 "/srv/$P_WORD"; chmod 0666 "/srv/$P_WORD/budget.csv"
