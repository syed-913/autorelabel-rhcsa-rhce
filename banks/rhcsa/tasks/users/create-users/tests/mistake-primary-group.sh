#!/usr/bin/env bash
# Common mistake: -g (primary group) instead of -G (supplementary).
groupadd -g "$P_GID" "$P_GROUP"
useradd -g "$P_GROUP" "$P_USER1"
useradd -g "$P_GROUP" "$P_USER2"
useradd -u "$P_UID3" -s /sbin/nologin "$P_USER3"
for u in "$P_USER1" "$P_USER2" "$P_USER3"; do echo "$u:$P_PASSWORD" | chpasswd; done
