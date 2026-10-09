#!/usr/bin/env bash
# Common mistake: installed into the default user path instead of the requested directory.
for c in ansible-posix community-general; do
  as_student ansible-galaxy collection install "$LAB_COLLECTIONS_URL/$c.tar.gz" -p /home/student/.ansible/collections
done
