#!/usr/bin/env bash
systemctl enable --now httpd
systemctl disable --now rpcbind.socket rpcbind.service
