#!/usr/bin/env bash
# Another type web servers may read: public_content_t (content shared by several services).
semanage fcontext -a -t public_content_t "/srv/$P_SITE(/.*)?"
restorecon -Rv "/srv/$P_SITE"
