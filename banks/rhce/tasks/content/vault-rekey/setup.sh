#!/usr/bin/env bash
content='---
salaries:
  - name: amira
    monthly: 5200
  - name: bruno
    monthly: 4800'
install -d -m 0700 /usr/local/libexec/autorelabel
printf '%s\n' "$content" | sha256sum | cut -d' ' -f1 > /usr/local/libexec/autorelabel/salaries.sha256
printf '%s\n' "$content" | student_write salaries.yml
pw="$(mktemp)"; echo "$P_OLD" > "$pw"; chmod 0644 "$pw"
as_student ansible-vault encrypt --vault-password-file "$pw" salaries.yml >/dev/null
rm -f "$pw"
