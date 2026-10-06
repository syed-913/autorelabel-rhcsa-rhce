#!/usr/bin/env bash
dnf -y -q install $P_PKGS
dnf -y -q remove "$P_REMOVE"
