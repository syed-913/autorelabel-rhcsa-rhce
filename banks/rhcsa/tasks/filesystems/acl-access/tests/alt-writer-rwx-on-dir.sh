#!/usr/bin/env bash
# The writer gets rwx on the directory, to create files there. The ACL mask then shows as
# group rwx in the mode bits (770), although nobody ran chmod.
dnf -y -q install acl
setfacl -m "u:$P_READER:r" "/srv/$P_WORD/budget.csv"
setfacl -m "u:$P_WRITER:rw" "/srv/$P_WORD/budget.csv"
setfacl -m "u:$P_READER:rx,u:$P_WRITER:rwx" "/srv/$P_WORD"
setfacl -d -m "u:$P_WRITER:rw" "/srv/$P_WORD"
