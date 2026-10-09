#!/usr/bin/env bash
install -d -m 0755 /var/www/html/ansible/files
tmp="$(mktemp -d)"
mkdir -p "$tmp/css"
echo "Site $P_WORD" > "$tmp/index.html"
echo "body { font-family: sans-serif; }" > "$tmp/css/site.css"
tar -C "$tmp" -czf "/var/www/html/ansible/files/site-$P_WORD.tar.gz" index.html css
rm -rf "$tmp"
chmod 0644 "/var/www/html/ansible/files/site-$P_WORD.tar.gz"
restorecon -R /var/www/html/ansible/files
