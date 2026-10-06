#!/usr/bin/env bash
su - "$P_USER" -c "echo '$P_PASSWORD' | sudo -S touch /root/$P_WORD-by-sudo" 2>/dev/null
