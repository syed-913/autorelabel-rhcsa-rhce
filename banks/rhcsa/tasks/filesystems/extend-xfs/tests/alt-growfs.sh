#!/usr/bin/env bash
lvextend -q -L "$((P_TARGET + 20))M" "$P_VG/datalv"
xfs_growfs "/srv/$P_VG" >/dev/null
