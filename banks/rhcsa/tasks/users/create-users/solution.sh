#!/usr/bin/env bash
groupadd -g "$P_GID" "$P_GROUP"
useradd -G "$P_GROUP" "$P_USER1"
useradd -G "$P_GROUP" "$P_USER2"
useradd -u "$P_UID3" -s /sbin/nologin "$P_USER3"
for u in "$P_USER1" "$P_USER2" "$P_USER3"; do echo "$u:$P_PASSWORD" | chpasswd; done
