#!/usr/bin/env bash
dnf -y -q install acl
setfacl -m "u:$P_READER:r" "/srv/$P_WORD/budget.csv"
setfacl -m "u:$P_WRITER:rw" "/srv/$P_WORD/budget.csv"
setfacl -m "u:$P_READER:rx,u:$P_WRITER:rx" "/srv/$P_WORD"
setfacl -d -m "u:$P_WRITER:rw" "/srv/$P_WORD"
