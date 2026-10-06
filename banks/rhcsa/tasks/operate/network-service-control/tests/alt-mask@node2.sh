#!/usr/bin/env bash
systemctl enable --now httpd
systemctl mask --now rpcbind.socket rpcbind.service
