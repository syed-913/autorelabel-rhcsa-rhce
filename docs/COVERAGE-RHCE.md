# RHCE objective coverage

Objectives are verbatim from Red Hat's exam page (https://www.redhat.com/en/services/training/ex294-red-hat-certified-engineer-rhce-exam-red-hat-enterprise-linux), checked 2026-10-03.
Every objective line is split into independently testable *facets*.

- **55** tasks
- **57/57** objective lines have a primary task
- **57/57** objective lines have 2+ tasks
- **63/63** facets covered

Legend: 🟢 easy (10 pts) · 🟡 medium (15 pts) · 🔴 hard (20 pts) · ✅ self-tested on a real RHEL 10 VM

## Be able to perform all tasks expected of a Red Hat Certified System Administrator

### ✅ Understand and use essential tools

- essential tools on managed nodes: 🟡 `archive`, 🟡 `archive-fetch`, 🟢 `register-report`

### ✅ Operate running systems

- operate running systems: 🟡 `services-targets`, 🟡 `ansible-doc`, 🟡 `find-module`

### ✅ Configure local storage

- local storage: 🔴 `lvm-storage`, 🟡 `partition-mount`

### ✅ Create and configure file systems

- file systems: 🔴 `lvm-storage`, 🟡 `partition-mount`

### ✅ Deploy, configure, and maintain systems

- deploy, configure and maintain: 🟢 `repos`, 🟡 `timesync-system-role`

### ✅ Manage users and groups

- users and groups: 🟡 `users-groups`, 🔴 `vault-users`

### ✅ Manage security

- security: 🟡 `firewall-rules`, 🟡 `selinux-modules`, 🔴 `selinux-system-role`

### ✅ Be able to analyze simple shell scripts

- predict what a script does: 🟢 `script-predict`
- find and fix a bug in a script: 🟡 `script-fix`

## Understand core components of Ansible

### ✅ Inventories

- inventory structure and host selection: 🟡 `ansible-setup`, 🟡 `group-vars`, 🟡 `navigator-inventory`

### ✅ Modules

- use modules with correct arguments (FQCN): 🟡 `ansible-doc`, 🟢 `deploy-files`

### ✅ Variables

- play and task variables: 🟡 `template-conditionals`, 🟡 `playbook-to-role`, 🟢 `vars-files`, 🟡 `motd-role`
- host_vars / group_vars: 🟡 `group-vars`, 🟡 `navigator-inventory`

### ✅ Facts

- use gathered facts: 🔴 `hosts-template`, 🟡 `conditional-tasks`, 🔴 `hardware-report`
- custom (local) facts: 🟡 `custom-facts`

### ✅ Loops

- loop over lists and dicts: 🟡 `users-groups`, 🔴 `hosts-template`, 🔴 `vault-users`, 🔴 `hardware-report`, 🟡 `loops-dirs`, 🟢 `vars-files`

### ✅ Conditional tasks

- conditional tasks with when: 🔴 `vault-users`, 🟡 `conditional-tasks`

### ✅ Plays

- multiple plays with different hosts/become: 🟡 `multi-play`, 🔴 `requirements-balancer`

### ✅ Handling task failure

- block/rescue/always: 🔴 `block-rescue-lvm`, 🔴 `web-rescue`
- failed_when / changed_when / ignore_errors: 🟡 `failed-when`

### ✅ Playbooks

- write and run playbooks: 🟡 `multi-play`, 🟡 `commit-push`

### ✅ Configuration files

- ansible.cfg location and settings: 🟡 `ansible-cfg-tuning`, 🟡 `ansible-setup`

### ✅ Roles

- role structure and use: 🟡 `playbook-to-role`, 🔴 `create-apache`, 🟡 `motd-role`, 🔴 `requirements-balancer`

### ✅ Use provided documentation to look up specific information about Ansible modules and commands

- find module options with ansible-doc / ansible-navigator doc: 🟡 `ansible-doc`, 🟡 `find-module`

## Configure Ansible

### ✅ Create and modify ansible.cfg

- ansible.cfg with inventory, remote_user, become, roles_path: 🟡 `ansible-cfg-tuning`, 🟡 `ansible-setup`

### ✅ Modify ansible-navigator.yml

- ansible-navigator.yml image, pull policy, mode: 🟢 `navigator-yml`, 🟡 `extension-settings`

### ✅ Create a static host inventory file

- static inventory file: 🟡 `ansible-setup`, 🟡 `navigator-inventory`

### ✅ Create and use static inventories to define groups of hosts

- groups and children groups: 🟡 `ansible-setup`, 🟡 `navigator-inventory`

## Configure Ansible managed nodes

### ✅ Configure Ansible managed nodes

- prepare managed nodes: 🟡 `authorized-key`, 🟡 `managed-access`

### ✅ Create and distribute SSH keys to managed nodes

- generate and distribute SSH keys: 🟡 `authorized-key`, 🟡 `managed-access`

### ✅ Configure privilege escalation on managed nodes

- sudo/become on managed nodes: 🟡 `multi-play`, 🟡 `managed-access`

### ✅ Deploy files to managed nodes

- deploy files to managed nodes: 🟡 `custom-facts`, 🟢 `clone-branch`, 🟢 `deploy-files`

## Run playbooks

### ✅ Know how to run playbooks with ansible-navigator and ansible-playbook

- run with ansible-navigator and ansible-playbook: 🟡 `navigator-run`, 🔴 `devcontainer-run`

### ✅ Use ansible-navigator to find new modules in available Ansible Content Collections and use them

- find modules with ansible-navigator collections/doc: 🟡 `at-job`, 🟡 `find-module`

### ✅ Use ansible-navigator to create inventories and configure the Ansible environment

- create and inspect inventories with ansible-navigator: 🟡 `navigator-inventory`
- configure the Ansible environment for ansible-navigator (settings file: image, pull policy, mode, artifacts): 🟢 `navigator-yml`, 🟡 `navigator-inventory`

## Perform basic source control operations using Git

### ✅ Clone a Git repository

- clone a repository: 🟢 `clone-branch`, 🟡 `commit-push`, 🟡 `release-branch`

### ✅ Add files to a Git repository

- add, commit and push files: 🟡 `commit-push`, 🟡 `editor-push`, 🟡 `release-branch`

## Be familiar with Visual Studio Code (VS Code) and be able to perform the following tasks from within the editor:

### ✅ Create playbooks and push them to a Git repository

- create a playbook in the editor and push it: 🟡 `editor-push`, 🟡 `release-branch`

### ✅ Configure ansible-navigator

- configure ansible-navigator from the editor: 🟢 `navigator-yml`, 🟡 `extension-settings`

### ✅ Run playbooks using an Ansible development container

- run a playbook in the Ansible development container: 🟡 `navigator-run`, 🔴 `devcontainer-run`

## Create Ansible plays and playbooks

### ✅ Know how to work with commonly used Ansible modules

- builtin/posix/general modules: 🟡 `archive-fetch`, 🟡 `ansible-doc`, 🔴 `hardware-report`, 🟡 `loops-dirs`

### ✅ Use variables to retrieve the results of running a command

- register command results: 🟡 `failed-when`, 🟡 `multi-play`, 🟡 `conditional-play`, 🟢 `register-report`

### ✅ Use conditionals to control play execution

- conditionals controlling execution: 🟢 `issue-per-group`, 🟢 `packages-groups`, 🟡 `conditional-play`

### ✅ Configure error handling

- error handling in plays: 🔴 `block-rescue-lvm`, 🟡 `failed-when`, 🔴 `web-rescue`

### ✅ Create playbooks to configure systems to a specified state

- idempotent desired-state playbooks: 🟢 `repos`, 🟡 `navigator-run`

## Use roles and Ansible Content Collections

### ✅ Create and work with roles

- create a role: 🟡 `playbook-to-role`, 🔴 `create-apache`

### ✅ Install roles and use them in playbooks

- install roles from requirements.yml: 🟡 `motd-role`, 🔴 `requirements-balancer`

### ✅ Install Content Collections and use them in playbooks

- install collections: 🟢 `collections`
- use modules from installed collections in playbooks (FQCN): 🟡 `firewall-rules`, 🟡 `selinux-modules`

### ✅ Obtain a set of related roles, supplementary modules, and other content from content collections, and use them in a playbook.

- use roles from a collection (e.g. system roles): 🔴 `selinux-system-role`, 🟡 `timesync-system-role`

## Automate standard RHCSA tasks using Ansible modules that work with:

### ✅ Software packages and repositories

- dnf / yum_repository: 🟡 `at-job`, 🟢 `packages-groups`, 🟢 `repos`, 🟡 `services-targets`, 🟢 `vars-files`, 🟡 `conditional-play`, 🟡 `navigator-run`

### ✅ Services

- service / systemd: 🟡 `at-job`, 🟡 `edit-config-lines`, 🟡 `services-targets`, 🟡 `multi-play`, 🔴 `web-rescue`, 🔴 `create-apache`, 🟡 `editor-push`

### ✅ Firewall rules

- firewalld: 🟡 `firewall-rules`, 🟡 `multi-play`, 🔴 `create-apache`

### ✅ File systems

- filesystem / mount: 🔴 `lvm-storage`, 🟡 `partition-mount`, 🔴 `block-rescue-lvm`

### ✅ Storage devices

- parted / lvg / lvol: 🔴 `lvm-storage`, 🟡 `partition-mount`, 🔴 `block-rescue-lvm`

### ✅ File content

- copy / lineinfile / blockinfile / template: 🟡 `edit-config-lines`, 🟢 `issue-per-group`, 🟡 `group-vars`, 🔴 `hardware-report`, 🟢 `deploy-files`, 🟢 `register-report`

### ✅ Archiving

- archive / unarchive: 🟡 `archive`, 🟡 `archive-fetch`

### ✅ Task scheduling

- cron / at: 🟡 `at-job`, 🟢 `cron-job`

### ✅ Security

- selinux / seboolean / sefcontext / seport: 🟡 `selinux-modules`, 🔴 `selinux-system-role`

### ✅ Users and groups

- user / group: 🟢 `cron-job`, 🟡 `users-groups`, 🔴 `vault-users`, 🟡 `loops-dirs`, 🟡 `authorized-key`

## Manage content

### ✅ Create and use templates to create customized configuration files

- Jinja2 templates with facts/loops/conditionals: 🔴 `hosts-template`, 🟡 `template-conditionals`, 🟡 `playbook-to-role`, 🔴 `create-apache`

### ✅ Use Ansible Vault in playbooks to protect sensitive data

- encrypt variables and use them in playbooks: 🟢 `vault-rekey`, 🔴 `vault-users`
