# RHCSA objective coverage

Objectives are verbatim from Red Hat's exam page (https://www.redhat.com/en/services/training/ex200-red-hat-certified-system-administrator-rhcsa-exam), checked 2026-10-03.
Every objective line is split into independently testable *facets*.

- **102** tasks
- **62/62** objective lines have a primary task
- **62/62** objective lines have 2+ tasks
- **138/139** facets covered

Legend: 🟢 easy (10 pts) · 🟡 medium (15 pts) · 🔴 hard (20 pts) · ✅ self-tested on a real RHEL 10 VM

## Understand and use essential tools

### ✅ Access a shell prompt and issue commands with correct syntax

- compose commands with options/arguments to produce a required result: 🟢 `find-copy-files`, 🟢 `ssh-remote-command`

### ✅ Use input-output redirection (>, >>, |, 2>, etc.)

- overwrite a file with command output (>): 🟡 `find-log-messages`, 🟢 `grep-save-lines`, 🟢 `redirection`
- append command output to a file (>>): 🟢 `redirection`
- pipe output between commands (|): 🟢 `redirection`
- capture or discard standard error (2>): 🟢 `redirection`
- capture stdout and stderr together (&> or 2>&1): 🟢 `redirection`

### ✅ Use grep and regular expressions to analyze text

- select lines matching a fixed pattern: 🟢 `grep-save-lines`
- use anchors, character classes or extended regex: 🟡 `grep-regex`
- save matching lines to a file in original order: 🟡 `grep-regex`, 🟢 `grep-save-lines`

### ✅ Access remote systems using SSH

- run a command on a remote system over SSH: 🟢 `secure-copy`, 🟢 `ssh-remote-command`
- log in to a remote system as a specific user: 🟡 `ssh-keys`

### ✅ Log in and switch users in multi-user targets

- switch to another user with a login shell (su -): 🟢 `edit-as-user`
- obtain a root shell with sudo: 🟢 `sudo-as-user`

### ✅ Archive, compress, unpack, and uncompress files using tar, gzip, and bzip2

- create a gzip-compressed tar archive: 🟢 `archive-gzip-extract`
- create a bzip2-compressed tar archive: 🟢 `archive-bzip2`
- extract an archive to a given directory: 🟢 `archive-gzip-extract`
- compress or uncompress a single file with gzip/gunzip: 🟢 `compress-files`
- compress or uncompress a single file with bzip2/bunzip2: 🟢 `compress-files`

### ✅ Create and edit text files

- create or modify a text file with exact content: 🟢 `edit-as-user`, 🟢 `info-date-format`

### ✅ Create, delete, copy, and move files and directories

- create directory trees: 🟢 `find-copy-files`, 🟢 `tidy-files`
- copy files preserving ownership, mode and timestamps: 🟢 `find-copy-files`
- move or rename files: 🟢 `tidy-files`
- delete files and directories selectively: 🟢 `tidy-files`
- locate files by owner, size or name and act on them: 🟢 `find-copy-files`, 🟡 `fix-broken-link`

### ✅ Create hard and soft links

- create a hard link: 🟡 `fix-broken-link`, 🟢 `links`
- create a symbolic link: 🟡 `fix-broken-link`, 🟢 `links`

### ✅ List, set, and change standard ugo/rwx permissions

- set permissions with symbolic notation: 🟢 `permissions`
- set permissions with octal notation: 🟢 `permissions`
- change user and group ownership: 🟡 `collaborative-dir`, 🟢 `permissions`

### ✅ Locate, read, and use system documentation including man, info, and files in /usr/share/doc

- find information in a man page (including man -k): 🟢 `man-search`
- find information in an info page: 🟢 `info-date-format`
- find information in /usr/share/doc: 🟢 `info-date-format`

## Manage software

### ✅ Configure access to RPM repositories

- configure BaseOS and AppStream repositories from a URL: 🟢 `configure-repos`
- configure GPG checking/keys for a repository: 🟡 `update-from-repo`, 🟢 `configure-repos`

### ✅ Install and remove RPM software packages

- install packages: 🟢 `at-job`, 🟢 `install-local-rpm`, 🟡 `acl-access`, 🟡 `nfs-mount`, 🟡 `vfat-uuid`, 🟡 `flatpak-remote-install`, 🟢 `install-remove-packages`
- remove packages: 🟢 `install-remove-packages`
- install a package group: 🟢 `package-group`

### ✅ Configure access to Flatpak repositories

- add a Flatpak remote from a URL: 🟡 `flatpak-user-remote`
- add a Flatpak remote from a .flatpakrepo file: 🟡 `flatpak-remote-install`
- choose system-wide vs per-user remotes: 🟡 `flatpak-remote-install`, 🟡 `flatpak-user-remote`

### ✅ Install and remove Flatpak software packages

- install a Flatpak application: 🟡 `flatpak-remote-install`
- uninstall a Flatpak application: 🟡 `flatpak-ref-swap`
- install from a .flatpakref file: 🟡 `flatpak-ref-swap`

## Create simple shell scripts

### ✅ Conditionally execute code (use of: if, test, [], etc.)

- branch on a test/[ ] condition: 🟡 `file-loop`, 🟡 `path-type`, 🟡 `user-lookup`
- branch on a command's exit status and set exit codes: 🟡 `path-type`, 🟡 `user-lookup`

### ✅ Use Looping constructs (for, etc.) to process file, command line input

- loop over lines of a file: 🟡 `file-loop`
- loop over command-line arguments: 🟡 `arg-loop`

### ✅ Process script inputs ($1, $2, etc.)

- use positional parameters: 🟡 `arg-loop`, 🟡 `path-type`, 🟡 `user-lookup`
- validate the number of arguments ($#): 🟡 `user-lookup`

### ✅ Processing output of shell commands within a script

- use command substitution $( ): 🟡 `file-loop`, 🟢 `system-report`

## Operate running systems

### ✅ Boot, reboot, and shut down a system normally

- reboot or shut down cleanly so changes apply: 🟡 `kernel-args`, 🔴 `boot-emergency-fstab`

### ✅ Boot systems into different targets manually

- boot into rescue or emergency target to repair a system: 🔴 `boot-emergency-fstab`, 🔴 `boot-emergency-kernel-arg`
- switch the running system to another target (practice drill: leaves nothing to grade after a reboot): 🟢 `graphical-target`

### ✅ Interrupt the boot process in order to gain access to a system

- reset a forgotten root password via the boot loader (rd.break): 🔴 `root-account-expired`, 🔴 `root-password-reset`

### ✅ Identify CPU/memory intensive processes and kill processes

- identify the most CPU- or memory-intensive process: 🟡 `cpu-hog`, 🔴 `memory-hog-respawn`
- terminate a process and keep it from returning: 🟡 `cpu-hog`, 🔴 `memory-hog-respawn`

### ✅ Adjust  process scheduling

- set or change process niceness: 🟡 `nice-cron-job`, 🟡 `process-priority`

### ✅ Manage tuning profiles

- select a specific tuned profile: 🟢 `tuned-profile`
- apply the recommended tuned profile: 🟢 `tuned-profile`, 🟢 `tuned-recommended`

### ✅ Locate and interpret system log files and journals

- filter the journal by unit, priority or time: 🟡 `find-log-messages`, 🟡 `journal-size-limit`, 🟢 `persistent-journal`
- find information in /var/log files: 🟡 `find-log-messages`

### ✅ Preserve system journals

- make the journal persistent across reboots: 🟡 `journal-size-limit`, 🟢 `persistent-journal`

### ✅ Start, stop, and check the status of network services

- start, stop and check network services: 🟢 `services-enable`, 🟡 `network-service-control`

### ✅ Securely transfer files between systems

- copy files between systems with scp/sftp: 🟢 `secure-copy`
- synchronize files between systems with rsync over SSH: 🟡 `rsync-mirror`, 🟢 `secure-copy`

## Configure local storage

### ✅ List, create, and delete partitions on GPT disks

- create GPT partitions of a given size: 🟡 `xfs-and-ext4`, 🟡 `gpt-partitions`, 🟡 `swap-partition`
- delete a partition: 🟡 `gpt-partitions`

### ✅ Create and remove physical volumes

- initialize a physical volume: 🔴 `lvm-create`, 🟡 `vg-extend`
- remove a physical volume: 🟡 `pv-remove`

### ✅ Assign physical volumes to volume groups

- create a volume group (including a specific extent size): 🔴 `lvm-create`
- add a physical volume to an existing volume group: 🔴 `extend-ext4`, 🟡 `pv-remove`, 🟡 `vg-extend`

### ✅ Create and delete logical volumes

- create a logical volume by size: 🟡 `swap-lv`
- create a logical volume by number of extents: 🔴 `lvm-create`
- delete a logical volume: 🟢 `lv-delete`

### ✅ Configure systems to mount file systems at boot by universally unique ID (UUID) or label

- persistent mount by UUID: 🟡 `vfat-uuid`, 🔴 `boot-emergency-fstab`, 🔴 `lvm-create`
- persistent mount by file system label: 🟡 `mount-label`

### ✅ Add new partitions and logical volumes, and swap to a system non-destructively

- add a partition alongside existing ones without data loss: 🟡 `gpt-partitions`, 🟡 `mount-label`, 🟡 `swap-partition`, 🟡 `vg-extend`
- add a logical volume to a VG in use: 🟡 `swap-lv`
- add persistent swap on a partition: 🟡 `swap-partition`
- add persistent swap on a logical volume: 🟡 `swap-lv`

## Create and configure file systems

### ✅ Create, mount, unmount, and use VFAT, ext4, and XFS file systems

- create and mount a VFAT file system: 🟡 `vfat-uuid`
- create and mount an ext4 file system: 🟡 `xfs-and-ext4`, 🟡 `mount-label`
- create and mount an XFS file system (>= 300 MB on RHEL 10): 🟡 `xfs-and-ext4`, 🔴 `lvm-create`

### ✅ Mount and unmount network file systems using NFS

- mount an NFS export persistently: 🟡 `autofs-indirect`, 🟡 `nfs-mount`

### ✅ Configure autofs

- indirect automount map: 🟡 `autofs-indirect`
- wildcard map for home directories: 🔴 `autofs-home-wildcard`
- direct automount map: 🟡 `autofs-direct`

### ✅ Extend existing logical volumes

- extend an LV holding XFS and grow the file system: 🟡 `extend-xfs`
- extend an LV holding ext4 and resize the file system: 🔴 `extend-ext4`

### ✅ Diagnose and correct file permission problems

- collaborative directory with setgid: 🟡 `collaborative-dir`
- restrict deletion with the sticky bit: 🟡 `collaborative-dir`
- grant access with POSIX ACLs: 🟡 `acl-access`
- diagnose and fix wrong ownership/permissions: 🔴 `fix-home-access`

## Deploy, configure, and maintain systems

### ✅ Schedule tasks using at, cron and systemd timer units

- schedule a one-time job with at: 🟢 `at-job`
- schedule a recurring job in a user crontab: 🟢 `cron-user`, 🟡 `nice-cron-job`
- schedule a system cron job: 🟢 `cron-system`, 🔴 `memory-hog-respawn`
- schedule with a systemd timer unit: 🟡 `systemd-timer`

### ✅ Start and stop services and configure services to start automatically at boot

- enable a service at boot: 🟢 `at-job`, 🟢 `chrony-client`, 🟢 `services-enable`, 🟡 `systemd-timer`, 🔴 `selinux-port-web`
- disable or mask a service: 🟢 `services-enable`, 🟡 `cpu-hog`, 🟡 `network-service-control`

### ✅ Configure systems to boot into a specific target automatically

- set the default boot target: 🟢 `default-target`, 🟢 `graphical-target`, 🔴 `boot-emergency-kernel-arg`

### ✅ Configure time service clients

- configure chrony to use a given time server: 🟢 `chrony-client`, 🟡 `timezone-and-ntp`

### ✅ Install and update software packages from Red Hat Content Delivery Network, a remote repository, or from the local file system

- install/update from a remote repository: 🟡 `update-from-repo`
- install from a local RPM file or local repository: 🟢 `install-local-rpm`
- install from the Red Hat CDN (optional drill; requires your own subscription): *not yet covered* *(optional drill)*

### ✅ Modify the system bootloader

- add or remove kernel command-line arguments: 🟡 `kernel-args`, 🔴 `boot-emergency-kernel-arg`, 🟡 `selinux-enforcing-kernel-arg`
- change GRUB settings such as the timeout: 🟢 `grub-timeout`

## Manage basic networking

### ✅ Configure IPv4 and IPv6 addresses

- static IPv4 address, gateway and DNS: 🟡 `configure-node1`
- static IPv6 address: 🟡 `ipv6-address`

### ✅ Configure hostname resolution

- set the persistent hostname: 🟡 `configure-node1`, 🟡 `dns-client`
- static name resolution in /etc/hosts: 🟢 `hosts-file`
- configure DNS servers/search domain: 🟡 `configure-node1`, 🟡 `dns-client`

### ✅ Configure network services to start automatically at boot

- network service and connection start at boot: 🟡 `configure-node1`, 🟡 `connection-autoconnect`

### ✅ Restrict network access using firewalld and firewall-cmd

- restrict access by source with a rich rule or zone: 🔴 `firewall-rich-rule`
- remove an allowed service or port: 🟢 `firewall-remove-services`

## Manage users and groups

### ✅ Create, delete, and modify local user accounts

- create a user with specific attributes (UID, shell, home, comment): 🟢 `create-users`
- modify an existing user: 🟢 `modify-delete-users`
- delete a user (with or without home): 🟢 `modify-delete-users`

### ✅ Change passwords and adjust password aging for local user accounts

- set a user's password: 🔴 `root-password-reset`, 🟢 `create-users`, 🟡 `password-aging`
- set password aging for an existing user: 🔴 `root-account-expired`, 🟡 `password-aging`
- set password aging defaults for new users: 🟡 `password-aging`

### ✅ Create, delete, and modify local groups and group memberships

- create a group with a specific GID: 🟢 `create-users`, 🟢 `group-management`
- manage supplementary group membership: 🟢 `create-users`, 🟢 `group-management`, 🟢 `modify-delete-users`, 🟡 `sudo-access`
- delete a group: 🟢 `group-management`, 🟢 `modify-delete-users`

### ✅ Configure privileged access

- sudo rights for a group: 🟡 `sudo-access`
- sudo rights limited to specific commands / NOPASSWD: 🟡 `sudo-access`

## Manage security

### ✅ Configure firewall settings using firewall-cmd/firewalld

- permanently allow a service: 🔴 `firewall-rich-rule`, 🟢 `firewall-services`, 🟡 `firewall-zone`
- permanently allow a port: 🟢 `firewall-services`, 🔴 `selinux-port-web`, 🔴 `selinux-ssh-port`
- work with zones (default zone, interface binding): 🟡 `firewall-zone`

### ✅ Manage default file permissions

- default permissions for a specific user: 🟢 `umask-user`
- system-wide default permissions: 🟡 `umask-system`

### ✅ Configure key-based authentication for SSH

- generate a key pair and authorize it on another system: 🔴 `ssh-key-only-user`, 🟡 `ssh-keys`

### ✅ Set enforcing and permissive modes for SELinux

- set enforcing mode persistently: 🟢 `selinux-enforcing`, 🟡 `selinux-enforcing-kernel-arg`
- set permissive mode persistently: 🟢 `selinux-permissive`

### ✅ List and identify SELinux file and process context

- identify a file's SELinux context: 🟢 `selinux-contexts`, 🟡 `selinux-fcontext-web`
- identify a process's SELinux context: 🟢 `selinux-contexts`

### ✅ Restore default file contexts

- restore default contexts with restorecon: 🔴 `fix-home-access`, 🟡 `selinux-fcontext-web`
- persistent file-context rule with semanage fcontext: 🟡 `selinux-fcontext-web`

### ✅ Manage SELinux port labels

- label a non-standard port for a service: 🔴 `selinux-port-web`, 🔴 `selinux-ssh-port`

### ✅ Use Boolean settings to modify system SELinux settings

- set a boolean persistently: 🟢 `selinux-boolean`, 🟡 `selinux-find-boolean`
