#!/usr/bin/env bash
curl -fsSo /root/labtools-1.0-1.el10.noarch.rpm "http://$LAB_UTILITY_FQDN/rpms/labtools-1.0-1.el10.noarch.rpm"
dnf -y -q install /root/labtools-1.0-1.el10.noarch.rpm
