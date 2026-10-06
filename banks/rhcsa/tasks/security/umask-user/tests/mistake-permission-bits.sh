#!/usr/bin/env bash
# Common mistake: writing the desired permissions instead of the umask.
echo "umask 0640" >> "/home/$P_USER/.bashrc"
