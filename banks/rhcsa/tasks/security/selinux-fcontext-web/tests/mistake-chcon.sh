#!/usr/bin/env bash
# Common mistake: chcon works now but is not a policy rule (lost on relabel; new files wrong).
chcon -R -t httpd_sys_content_t "/srv/$P_SITE"
