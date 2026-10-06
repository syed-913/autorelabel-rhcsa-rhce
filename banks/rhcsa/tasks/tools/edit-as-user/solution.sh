#!/usr/bin/env bash
su - "$P_USER" -c "printf 'project=%s\nowner=%s\n' '$P_WORD' '$P_USER' > ~/'$P_WORD'.txt"
