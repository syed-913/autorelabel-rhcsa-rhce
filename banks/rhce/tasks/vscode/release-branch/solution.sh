#!/usr/bin/env bash
# Stand-in for the editor's Source Control actions (switch branch, commit, push).
helper="!f() { echo username=student; echo password=$AR_STUDENT_PASSWORD; }; f"
d=/home/student/git/lab-content
runuser -u student -- mkdir -p /home/student/git
test -d "$d/.git" || as_student git -c credential.helper="$helper" clone -q "$LAB_GIT_CONTENT_URL" "$d"
as_student git config --global user.name "Lab Student"
as_student git config --global user.email student@lab.example.com
as_student git -C "$d" switch -q release
printf 'lab-content release %s\n' "$P_VER" > "$d/site/index.html"
chown student:student "$d/site/index.html"
as_student git -C "$d" commit -q -am "Release $P_VER"
as_student git -C "$d" -c credential.helper="$helper" push -q origin release
