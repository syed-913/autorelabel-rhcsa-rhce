#!/usr/bin/env bash
getent group "$P_GROUP" >/dev/null || groupadd "$P_GROUP"
ar_user "$P_ADMIN" "$P_PASSWORD"
ar_user "$P_OPERATOR" "$P_PASSWORD"
