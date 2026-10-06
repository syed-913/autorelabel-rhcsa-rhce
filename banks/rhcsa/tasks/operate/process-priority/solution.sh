#!/usr/bin/env bash
mkdir -p "/etc/systemd/system/$P_WORD-indexer.service.d"
printf '[Service]\nNice=%s\n' "$P_NICE" > "/etc/systemd/system/$P_WORD-indexer.service.d/nice.conf"
systemctl daemon-reload
systemctl restart "$P_WORD-indexer.service"
