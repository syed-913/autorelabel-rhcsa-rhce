#!/usr/bin/env bash
# Common mistake: fixing only the visible problem (ownership).
chown -R "$P_USER:$P_USER" "/home/$P_USER"
