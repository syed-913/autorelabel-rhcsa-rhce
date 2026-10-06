#!/usr/bin/env bash
for u in "$P_OWNER" "$P_READER" "$P_WRITER"; do ar_user "$u" "Lab-$RANDOM-pw"; done
mkdir -p "/srv/$P_WORD"; echo "q1,q2\n10,20" > "/srv/$P_WORD/budget.csv"
chown -R "$P_OWNER:" "/srv/$P_WORD"; chmod 0750 "/srv/$P_WORD"; chmod 0640 "/srv/$P_WORD/budget.csv"
