#!/usr/bin/env bash
lvextend -q -r -L "$((P_TARGET + 20))M" "$P_VG/datalv"
