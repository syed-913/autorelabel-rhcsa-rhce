#!/usr/bin/env bash
chown "$P_USER:$P_GROUP" "/srv/$P_WORD/report.txt" "/srv/$P_WORD/run.sh"
chmod 640 "/srv/$P_WORD/report.txt"
chmod u=rwx,g=rx,o= "/srv/$P_WORD/run.sh"
chown root:"$P_GROUP" "/srv/$P_WORD"
chmod 750 "/srv/$P_WORD"
