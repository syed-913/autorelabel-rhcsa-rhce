#!/usr/bin/env bash
systemctl start tuned
tuned-adm profile "$(tuned-adm recommend)"
