#!/usr/bin/env bash
mkdir -p "/data/$P_WORD" "/srv/$P_WORD" "/opt/$P_WORD/bin"
echo "readings for $P_WORD" > "/data/$P_WORD/2026.dat"
printf '#!/bin/sh\necho "%s cli ok"\n' "$P_WORD" > "/opt/$P_WORD/bin/$P_WORD-cli"
chmod 0755 "/opt/$P_WORD/bin/$P_WORD-cli"
