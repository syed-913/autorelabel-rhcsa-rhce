#!/usr/bin/env bash
getent group "$P_NEWGROUP" >/dev/null || groupadd "$P_NEWGROUP"
getent group "$P_OLDGROUP" >/dev/null || groupadd "$P_OLDGROUP"
ar_user "$P_KEEP" "Lab-$RANDOM-x" -G wheel -c "Temp"
ar_user "$P_GONE" "Lab-$RANDOM-y" -G "$P_OLDGROUP"
echo "important" > "/home/$P_GONE/notes.txt"; chown "$P_GONE:" "/home/$P_GONE/notes.txt"
touch "/var/spool/mail/$P_GONE"
