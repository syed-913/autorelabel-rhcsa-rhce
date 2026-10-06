#!/usr/bin/env bash
getent group "$P_GROUP" >/dev/null || groupadd "$P_GROUP"
ar_user "$P_USER" "Lab-$RANDOM-pw"
mkdir -p "/srv/$P_WORD"; chmod 0777 "/srv/$P_WORD"
echo "quarterly numbers" > "/srv/$P_WORD/report.txt"; chmod 0666 "/srv/$P_WORD/report.txt"
printf '#!/bin/sh\necho run\n' > "/srv/$P_WORD/run.sh"; chmod 0644 "/srv/$P_WORD/run.sh"
