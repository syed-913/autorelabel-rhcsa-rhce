# The lab

Every exam runs in a lab of a few virtual machines on your computer. This page describes them: what each VM is for, how they are connected, which accounts exist, and what the utility server provides. Only one lab exists at a time: starting an RHCSA exam removes the RHCE lab, and the other way round.

## The RHCSA lab

| VM | Address | Role | RAM (lite / standard) | Extra disks |
|---|---|---|---|---|
| `utility` | `.10` | The support server: repositories, DNS, time, NFS, Flatpak | 768 MB / 1 GB | none |
| `node1` | `.11` | Exam node | 1 GB / 1.5 GB | two: 8 GB and 4 GB |
| `node2` | `.12` | Exam node | 1 GB / 1.5 GB | one: 4 GB |

An RHCSA exam starts the way most real ones do:

- **node1 has no network** on its lab interface. You configure it from the console, and until then you can't SSH to it.
- **node2's root password is unknown.** You reset it by interrupting the boot.
- **No software repositories are configured** on either node. A task asks you to point them at the utility server.

## The RHCE lab

| VM | Address | Role | RAM (lite / standard) | Extra disks |
|---|---|---|---|---|
| `utility` | `.10` | The support server, plus a Git server and the Ansible content | 1 GB / 1 GB | none |
| `control` | `.20` | Where you work, as `student` | 2 GB / 2.5 GB (2 CPUs) | none |
| `node1` to `node3` (lite) or `node5` (standard) | `.21` and up | Managed nodes | 768 MB / 1 GB | one: 4 GB |

An RHCE exam starts from an empty project directory, `/home/student/ansible` on `control`. You write the inventory and `ansible.cfg`, give the `ansible` user SSH keys and sudo on the managed nodes, install the collections and configure the repositories, all with Ansible.

The inventory groups are given in the instructions:

| Group | lite profile | standard profile |
|---|---|---|
| `dev` | node1 | node1 |
| `test` | node2 | node2 |
| `prod` | node3 | node3, node4 |
| `balancers` | node2 | node5 |
| `webservers` | has `prod` as a child group | has `prod` as a child group |

`control` has what the real RHCE provides: `ansible-core` 2.16 and the RHEL system roles from the RHEL 10 DVD, `ansible-navigator` with an execution environment built offline from the DVD's packages, and **VS Code in your browser** (code-server with Red Hat's Ansible extension).

> **How do I open VS Code?**
> The instructions show the address, which is `http://127.0.0.1:18080` on your own computer. autorelabel forwards it from `control` over SSH, because browsers only allow the clipboard and the editor's web views on `localhost` or HTTPS. The password is the `student` password from the instructions. The forwarding stops when the exam ends.

> **Do the disks have the same names on every computer?**
> The names depend on the hypervisor: the extra disks are `/dev/vdb` and `/dev/vdc` with libvirt, and `/dev/sdb` and `/dev/sdc` with VirtualBox. Tasks always name the exact disk to use, so read the task text.

## Networks

The lab has two networks. Neither can reach the internet or your local network.

| Network | Default subnet | What it is for |
|---|---|---|
| **Lab** | `172.25.250.0/24` with libvirt, `192.168.60.0/24` with VirtualBox | The network you work on and configure. Host names are in `lab.example.com`. The gateway is `.1` (your computer's side of the network), and DNS is the utility server, `.10`. Some tasks also ask for IPv6 addresses on it. |
| **Management** | `192.168.250.0/24` | How autorelabel prepares and grades the lab. Each VM's interface on it is called `mgmt0`. |

> **Why is there a second network, and can I use it?**
> The management network is how autorelabel reaches the VMs without depending on your work: it prepares the tasks and runs the checks over `mgmt0`, logged in as the `vagrant` user. The real exam also has machinery like this that candidates never touch. Leave `mgmt0` and the `vagrant` account alone. If the grader loses access to a node, its tasks score 0, which is why the exam screen warns you within about two minutes.

> **What if these subnets clash with my own network?**
> The doctor checks for this. If one of them overlaps a network your computer already uses, change it in [Settings](08-settings.md).

## The utility server

The utility server stands in for the support server that the real exam provides. You use its services from the nodes, and you never log in to it or change it.

| Service | Address |
|---|---|
| BaseOS repository | `http://utility.lab.example.com/rhel10/BaseOS` |
| AppStream repository | `http://utility.lab.example.com/rhel10/AppStream` |
| Red Hat's signing key | `http://utility.lab.example.com/rhel10/RPM-GPG-KEY-redhat-release` |
| Flatpak repository (Red Hat's own Flatpaks: Firefox, Thunderbird and `com.redhat.Platform`) | `http://utility.lab.example.com/flatpak/repo`, or the `.flatpakrepo` file at `http://utility.lab.example.com/flatpak/lab.flatpakrepo` |
| DNS for `lab.example.com` | `utility.lab.example.com` |
| Time (NTP) | `utility.lab.example.com` |
| NFS shares | `utility.lab.example.com` |
| RHCE: Git server | `http://utility.lab.example.com/git/ansible.git` |
| RHCE: Ansible collections and roles | `http://utility.lab.example.com/ansible` |
| RHCE: container registry for the execution environment | `utility.lab.example.com:5000` |

The repositories are the BaseOS and AppStream content of your own DVD, so the nodes never need a subscription or the internet.

## Accounts and passwords

| Account | Where | Password |
|---|---|---|
| `root` | every node | Shown in the instructions, new for every exam. In an RHCSA exam, node2's is deliberately unknown. |
| `student` | `control` (RHCE) | Shown in the instructions. `student` may use sudo, and is also the Git user. |
| `ansible` | managed nodes (RHCE) | Shown in the instructions. Giving it keys and sudo is one of your tasks. |
| `vagrant` | every VM | Used only by autorelabel itself. Leave it alone. |

The passwords are short made-up words with two digits, such as `kimuve47`, chosen to be easy to type on a console.

> **I've lost the instructions. Where are the passwords?**
> Press `i` on the exam screen, or run `./autorelabel exam tasks`. The console also prints the root password when you connect to a node.

## Snapshots

autorelabel keeps two snapshots of the lab:

- **baseline:** the clean, freshly built lab. Every new exam starts from it, so nothing from an earlier exam carries over.
- **exam start:** the lab right after this exam's tasks were set up. **Retake** and **Reset to exam start** go back to it.

> **How much disk space does the lab use?**
> The VM disks only use the space actually written to them, so the whole lab, its snapshots and the box usually fit well within the 30 GB the requirements mention (40 GB for RHCE, which has more VMs and downloads its Ansible content).
