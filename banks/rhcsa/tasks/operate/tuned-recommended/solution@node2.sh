#!/usr/bin/env bash
systemctl enable --now tuned
tuned-adm profile "$(tuned-adm recommend)"
