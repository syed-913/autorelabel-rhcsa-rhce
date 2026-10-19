#!/usr/bin/env bash
# RHCE additions on the utility server: Git over smart HTTP, Ansible collections and roles
# over HTTP. Content was copied to /var/tmp/ar-content by the app. common.sh is prepended.
C=/var/tmp/ar-content
WEB=/var/www/html

step "Git server (smart HTTP)"
dnf -y -q install git httpd-tools >/dev/null
install -d -m 0755 /var/lib/git
if [[ ! -d /var/lib/git/ansible.git ]]; then
  git init -q --bare /var/lib/git/ansible.git
  git -C /var/lib/git/ansible.git config http.receivepack true
  seed="$(mktemp -d)"
  git -C "$seed" init -q -b main
  printf '# Lab Ansible repository\n\nPlaybooks for the lab live here.\n' > "$seed/README.md"
  git -C "$seed" add README.md
  git -C "$seed" -c user.name="Lab" -c user.email="lab@lab.example.com" commit -q -m "Initial commit"
  git -C "$seed" push -q /var/lib/git/ansible.git main
  rm -rf "$seed"
  git -C /var/lib/git/ansible.git symbolic-ref HEAD refs/heads/main
fi
# A second repository with two branches, for clone/checkout tasks.
if [[ ! -d /var/lib/git/lab-content.git ]]; then
  git init -q --bare /var/lib/git/lab-content.git
  seed="$(mktemp -d)"
  git -C "$seed" init -q -b main
  g() { git -C "$seed" -c user.name="Lab" -c user.email="lab@lab.example.com" "$@"; }
  mkdir -p "$seed/site"
  printf 'lab-content development snapshot\n' > "$seed/site/index.html"
  printf '# Lab content\n\nWeb content for the lab web servers.\n' > "$seed/README.md"
  g add -A; g commit -q -m "Initial content"
  git -C "$seed" checkout -q -b release
  printf 'lab-content release 2.4\n' > "$seed/site/index.html"
  g commit -q -am "Release 2.4"
  git -C "$seed" checkout -q main
  printf 'lab-content development snapshot (next)\n' > "$seed/site/index.html"
  g commit -q -am "Start next development cycle"
  git -C "$seed" push -q /var/lib/git/lab-content.git main release
  rm -rf "$seed"
  git -C /var/lib/git/lab-content.git symbolic-ref HEAD refs/heads/main
fi
# Plain repositories, only ever written by Apache: no shared (setgid) directories, which
# httpd.service's RestrictSUIDSGID=yes forbids git to create ("Operation not permitted").
chown -R apache:apache /var/lib/git
find /var/lib/git -type d -perm -g+s -exec chmod g-s {} +
htpasswd -bcB /etc/httpd/git.htpasswd student "$AR_STUDENT_PASSWORD" >/dev/null 2>&1
cat > /etc/httpd/conf.d/git.conf <<'CONF'
SetEnv GIT_PROJECT_ROOT /var/lib/git
SetEnv GIT_HTTP_EXPORT_ALL
ScriptAlias /git/ /usr/libexec/git-core/git-http-backend/
<Location /git>
    AuthType Basic
    AuthName "Lab Git"
    AuthUserFile /etc/httpd/git.htpasswd
    Require valid-user
</Location>
CONF
semanage fcontext -a -t httpd_sys_rw_content_t "/var/lib/git(/.*)?" 2>/dev/null || \
  semanage fcontext -m -t httpd_sys_rw_content_t "/var/lib/git(/.*)?"
restorecon -R /var/lib/git
semanage fcontext -a -t httpd_sys_script_exec_t /usr/libexec/git-core/git-http-backend 2>/dev/null || true
restorecon /usr/libexec/git-core/git-http-backend
setsebool -P httpd_enable_cgi on
# git-http-backend runs as httpd_sys_script_t, which may read and write the repositories but
# not memory-map them, and git maps its object files ("fatal: mmap failed: Permission denied").
printf '(allow httpd_sys_script_t httpd_sys_rw_content_t (file (map)))\n' > /tmp/autorelabel-git.cil
semodule -i /tmp/autorelabel-git.cil
rm -f /tmp/autorelabel-git.cil
systemctl reload httpd

step "Ansible collections and roles"
install -d -m 0755 "$WEB/ansible/collections" "$WEB/ansible/roles"
cp "$C"/collections/*.tar.gz "$WEB/ansible/collections/"
# Stable, version-less names too (task text stays the same when content is refreshed).
for f in "$C"/collections/*-*-*.tar.gz; do
  b="$(basename "$f" .tar.gz)"
  cp "$f" "$WEB/ansible/collections/${b%-*}.tar.gz"
done
for r in "$C"/roles/*/; do
  name="$(basename "$r")"
  tar -C "$C/roles" -czf "$WEB/ansible/roles/$name.tar.gz" "$name"
done
restorecon -R "$WEB/ansible"
rm -rf "$C"
