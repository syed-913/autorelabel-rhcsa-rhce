#!/usr/bin/env bash
# Common mistake: stopping rpcbind.service but not rpcbind.socket (systemd keeps port 111 open).
systemctl enable --now httpd
systemctl disable --now rpcbind.service
