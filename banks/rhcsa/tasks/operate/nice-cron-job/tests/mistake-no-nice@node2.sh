#!/usr/bin/env bash
echo "30 $P_HOUR * * * /usr/bin/tar -czf /tmp/$P_USER-home.tgz /home/$P_USER" | crontab -u "$P_USER" -
