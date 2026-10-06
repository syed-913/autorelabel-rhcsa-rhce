#!/usr/bin/env bash
curl -fsSo /tmp/labtools.rpm "http://$LAB_UTILITY_FQDN/rpms/labtools-1.0-1.el10.noarch.rpm"
rpm -i /tmp/labtools.rpm
rm -f /tmp/labtools.rpm
