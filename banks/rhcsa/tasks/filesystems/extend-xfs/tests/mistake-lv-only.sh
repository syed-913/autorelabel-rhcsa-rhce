#!/usr/bin/env bash
# Common mistake: extending the LV but not the file system.
lvextend -q -L "$((P_TARGET + 20))M" "$P_VG/datalv"
