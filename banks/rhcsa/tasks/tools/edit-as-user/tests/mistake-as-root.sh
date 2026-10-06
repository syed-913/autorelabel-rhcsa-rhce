#!/usr/bin/env bash
# Common mistake: creating the file as root (wrong owner).
printf 'project=%s\nowner=%s\n' "$P_WORD" "$P_USER" > "/home/$P_USER/$P_WORD.txt"
