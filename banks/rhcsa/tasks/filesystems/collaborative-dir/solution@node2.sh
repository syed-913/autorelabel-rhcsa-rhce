#!/usr/bin/env bash
mkdir -p "/common/$P_GROUP"
chown root:"$P_GROUP" "/common/$P_GROUP"
chmod 3770 "/common/$P_GROUP"
