#!/usr/bin/env bash
# Common mistake: a symbolic link where a hard link was asked for.
ln -s "/data/$P_WORD/2026.dat" "/srv/$P_WORD/current.dat"
ln -s "/opt/$P_WORD/bin/$P_WORD-cli" "/usr/local/bin/$P_WORD"
