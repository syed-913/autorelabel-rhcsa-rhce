#!/usr/bin/env bash
old="$(mktemp)"; echo "$P_OLD" > "$old"; chmod 0644 "$old"
printf '%s\n' "$P_NEW" | student_write salaries-pass.txt 0600
as_student ansible-vault rekey --vault-password-file "$old" --new-vault-password-file salaries-pass.txt salaries.yml
rm -f "$old"
