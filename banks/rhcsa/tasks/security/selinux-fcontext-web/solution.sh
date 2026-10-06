#!/usr/bin/env bash
semanage fcontext -a -t httpd_sys_content_t "/srv/$P_SITE(/.*)?"
restorecon -Rv "/srv/$P_SITE"
