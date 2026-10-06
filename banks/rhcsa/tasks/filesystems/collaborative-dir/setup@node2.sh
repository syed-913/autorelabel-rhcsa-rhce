#!/usr/bin/env bash
getent group "$P_GROUP" >/dev/null || groupadd "$P_GROUP"
ar_user "$P_USER1" "Lab-$RANDOM-pw" -G "$P_GROUP"
ar_user "$P_USER2" "Lab-$RANDOM-pw" -G "$P_GROUP"
