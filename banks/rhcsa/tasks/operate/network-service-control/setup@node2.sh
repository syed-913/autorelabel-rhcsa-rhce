#!/usr/bin/env bash
ar_install httpd rpcbind
systemctl disable --now httpd >/dev/null 2>&1 || true
systemctl enable --now rpcbind.socket rpcbind.service
