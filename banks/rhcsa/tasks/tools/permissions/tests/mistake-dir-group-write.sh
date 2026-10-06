#!/usr/bin/env bash
# Common mistake: 770 on the directory lets the group create files.
chown "$P_USER:$P_GROUP" "/srv/$P_WORD/report.txt" "/srv/$P_WORD/run.sh"
chmod 640 "/srv/$P_WORD/report.txt"; chmod 750 "/srv/$P_WORD/run.sh"
chown root:"$P_GROUP" "/srv/$P_WORD"; chmod 770 "/srv/$P_WORD"
