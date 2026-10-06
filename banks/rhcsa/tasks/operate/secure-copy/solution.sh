#!/usr/bin/env bash
mkdir -p /srv/incoming
# Self-test stand-in for "scp root@node2:/root/<word>-config.tar /srv/incoming/" (the result is
# byte-identical) and for "ssh root@node2 hostname > /root/node2-hostname.txt".
ar_gen_tar "/srv/incoming/$P_WORD-config.tar" "$P_WORD"
echo "$LAB_NODE2_FQDN" > /root/node2-hostname.txt
