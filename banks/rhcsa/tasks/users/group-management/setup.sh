#!/usr/bin/env bash
getent group "$P_OLDGROUP" >/dev/null || groupadd "$P_OLDGROUP"
getent group "legacy-$P_RENAMED" >/dev/null || groupadd "legacy-$P_RENAMED"
install -d /etc/autorelabel
getent group "legacy-$P_RENAMED" | cut -d: -f3 > "/etc/autorelabel/$P_RENAMED-gid"
ar_user "$P_U1" "Lab-$RANDOM-pw" -G "$P_OLDGROUP"
ar_user "$P_U2" "Lab-$RANDOM-pw" -G "$P_OLDGROUP"
