#!/usr/bin/env bash
# Common mistake: configuring only the existing users' ~/.bashrc.
echo "umask 027" >> "/home/$P_USER1/.bashrc"
echo "umask 027" >> "/home/$P_USER2/.bashrc"
