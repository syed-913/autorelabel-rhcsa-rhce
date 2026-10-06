#!/usr/bin/env bash
systemctl enable --now tuned
tuned-adm auto_profile
