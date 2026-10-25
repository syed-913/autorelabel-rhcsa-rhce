# Exam objectives covered

This page lists every objective line from Red Hat's current exam pages for the [RHCSA (EX200)](https://www.redhat.com/en/services/training/ex200-red-hat-certified-system-administrator-rhcsa-exam) and the [RHCE (EX294)](https://www.redhat.com/en/services/training/ex294-red-hat-certified-engineer-rhce-exam-red-hat-enterprise-linux), copied word for word. A ✅ means the task bank practises that line with at least two tasks.

> **Where do these lists come from, and can they go out of date?**
> They are generated from the task bank (`banks/<exam>/objectives.yaml` and every task's objective tags) with `./autorelabel bank coverage <exam> --write`, and the project's automatic tests fail if this page no longer matches the bank. When Red Hat changes an exam page, the objectives file is updated first, and any line without tasks shows up here as ⬜ until tasks are written for it.

> **What does "covered" mean exactly?**
> Each objective line is split into the specific skills it can test, called facets (for example, "Configure autofs" has a direct map, an indirect map and a wildcard home-directory map). A line counts as covered when it has a primary task, and the project's quality gate requires at least two tasks per line. The detailed reports, with every facet and the tasks that practise it, are [COVERAGE-RHCSA.md](../COVERAGE-RHCSA.md) and [COVERAGE-RHCE.md](../COVERAGE-RHCE.md).

<!-- objectives:rhcsa -->
## RHCSA (EX200): 62 of 62 objective lines covered, 102 tasks

**Understand and use essential tools**

- ✅ Access a shell prompt and issue commands with correct syntax
- ✅ Use input-output redirection (>, >>, |, 2>, etc.)
- ✅ Use grep and regular expressions to analyze text
- ✅ Access remote systems using SSH
- ✅ Log in and switch users in multi-user targets
- ✅ Archive, compress, unpack, and uncompress files using tar, gzip, and bzip2
- ✅ Create and edit text files
- ✅ Create, delete, copy, and move files and directories
- ✅ Create hard and soft links
- ✅ List, set, and change standard ugo/rwx permissions
- ✅ Locate, read, and use system documentation including man, info, and files in /usr/share/doc

**Manage software**

- ✅ Configure access to RPM repositories
- ✅ Install and remove RPM software packages
- ✅ Configure access to Flatpak repositories
- ✅ Install and remove Flatpak software packages

**Create simple shell scripts**

- ✅ Conditionally execute code (use of: if, test, [], etc.)
- ✅ Use Looping constructs (for, etc.) to process file, command line input
- ✅ Process script inputs ($1, $2, etc.)
- ✅ Processing output of shell commands within a script

**Operate running systems**

- ✅ Boot, reboot, and shut down a system normally
- ✅ Boot systems into different targets manually
- ✅ Interrupt the boot process in order to gain access to a system
- ✅ Identify CPU/memory intensive processes and kill processes
- ✅ Adjust  process scheduling
- ✅ Manage tuning profiles
- ✅ Locate and interpret system log files and journals
- ✅ Preserve system journals
- ✅ Start, stop, and check the status of network services
- ✅ Securely transfer files between systems

**Configure local storage**

- ✅ List, create, and delete partitions on GPT disks
- ✅ Create and remove physical volumes
- ✅ Assign physical volumes to volume groups
- ✅ Create and delete logical volumes
- ✅ Configure systems to mount file systems at boot by universally unique ID (UUID) or label
- ✅ Add new partitions and logical volumes, and swap to a system non-destructively

**Create and configure file systems**

- ✅ Create, mount, unmount, and use VFAT, ext4, and XFS file systems
- ✅ Mount and unmount network file systems using NFS
- ✅ Configure autofs
- ✅ Extend existing logical volumes
- ✅ Diagnose and correct file permission problems

**Deploy, configure, and maintain systems**

- ✅ Schedule tasks using at, cron and systemd timer units
- ✅ Start and stop services and configure services to start automatically at boot
- ✅ Configure systems to boot into a specific target automatically
- ✅ Configure time service clients
- ✅ Install and update software packages from Red Hat Content Delivery Network, a remote repository, or from the local file system
- ✅ Modify the system bootloader

**Manage basic networking**

- ✅ Configure IPv4 and IPv6 addresses
- ✅ Configure hostname resolution
- ✅ Configure network services to start automatically at boot
- ✅ Restrict network access using firewalld and firewall-cmd

**Manage users and groups**

- ✅ Create, delete, and modify local user accounts
- ✅ Change passwords and adjust password aging for local user accounts
- ✅ Create, delete, and modify local groups and group memberships
- ✅ Configure privileged access

**Manage security**

- ✅ Configure firewall settings using firewall-cmd/firewalld
- ✅ Manage default file permissions
- ✅ Configure key-based authentication for SSH
- ✅ Set enforcing and permissive modes for SELinux
- ✅ List and identify SELinux file and process context
- ✅ Restore default file contexts
- ✅ Manage SELinux port labels
- ✅ Use Boolean settings to modify system SELinux settings
<!-- /objectives:rhcsa -->

<!-- objectives:rhce -->
## RHCE (EX294): 57 of 57 objective lines covered, 55 tasks

**Be able to perform all tasks expected of a Red Hat Certified System Administrator**

- ✅ Understand and use essential tools
- ✅ Operate running systems
- ✅ Configure local storage
- ✅ Create and configure file systems
- ✅ Deploy, configure, and maintain systems
- ✅ Manage users and groups
- ✅ Manage security
- ✅ Be able to analyze simple shell scripts

**Understand core components of Ansible**

- ✅ Inventories
- ✅ Modules
- ✅ Variables
- ✅ Facts
- ✅ Loops
- ✅ Conditional tasks
- ✅ Plays
- ✅ Handling task failure
- ✅ Playbooks
- ✅ Configuration files
- ✅ Roles
- ✅ Use provided documentation to look up specific information about Ansible modules and commands

**Configure Ansible**

- ✅ Create and modify ansible.cfg
- ✅ Modify ansible-navigator.yml
- ✅ Create a static host inventory file
- ✅ Create and use static inventories to define groups of hosts

**Configure Ansible managed nodes**

- ✅ Configure Ansible managed nodes
- ✅ Create and distribute SSH keys to managed nodes
- ✅ Configure privilege escalation on managed nodes
- ✅ Deploy files to managed nodes

**Run playbooks**

- ✅ Know how to run playbooks with ansible-navigator and ansible-playbook
- ✅ Use ansible-navigator to find new modules in available Ansible Content Collections and use them
- ✅ Use ansible-navigator to create inventories and configure the Ansible environment

**Perform basic source control operations using Git**

- ✅ Clone a Git repository
- ✅ Add files to a Git repository

**Be familiar with Visual Studio Code (VS Code) and be able to perform the following tasks from within the editor:**

- ✅ Create playbooks and push them to a Git repository
- ✅ Configure ansible-navigator
- ✅ Run playbooks using an Ansible development container

**Create Ansible plays and playbooks**

- ✅ Know how to work with commonly used Ansible modules
- ✅ Use variables to retrieve the results of running a command
- ✅ Use conditionals to control play execution
- ✅ Configure error handling
- ✅ Create playbooks to configure systems to a specified state

**Use roles and Ansible Content Collections**

- ✅ Create and work with roles
- ✅ Install roles and use them in playbooks
- ✅ Install Content Collections and use them in playbooks
- ✅ Obtain a set of related roles, supplementary modules, and other content from content collections, and use them in a playbook.

**Automate standard RHCSA tasks using Ansible modules that work with:**

- ✅ Software packages and repositories
- ✅ Services
- ✅ Firewall rules
- ✅ File systems
- ✅ Storage devices
- ✅ File content
- ✅ Archiving
- ✅ Task scheduling
- ✅ Security
- ✅ Users and groups

**Manage content**

- ✅ Create and use templates to create customized configuration files
- ✅ Use Ansible Vault in playbooks to protect sensitive data
<!-- /objectives:rhce -->
