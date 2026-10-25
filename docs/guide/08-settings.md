# Settings

Open **Settings** from the home screen (or press `s` there), or use `./autorelabel config` on the command line. Settings are stored in `.workspace/config.json` inside the repository.

## Every setting

| In the Settings screen | `config` key | Default | What it does |
|---|---|---|---|
| Scoring | `scoring` | `partial` | `partial`: each check earns its share of the task's points. `strict`: a task scores only if every check passes. See [Grading](05-grading-and-results.md#how-the-points-are-calculated). |
| Show task difficulty during the exam | `show_difficulty_during_exam` | `false` | Shows easy, medium or hard next to each task during an exam. Practice always shows it. |
| Forgive host downtime | `forgive_downtime` | `true` | Time while your computer sleeps, has crashed or is off doesn't count against the exam clock. Turn it off for a strict wall clock. |
| Warnings before the end | `warnings_minutes` | `30,10,5,1` | When the time warnings appear, in minutes before the end. |
| Resource profile | `profile` | `lite` | `lite` or `standard`: how much memory the VMs get, and for RHCE how many managed nodes there are (3 or 5). See [The lab](04-the-lab.md). |
| Lab storage directory | `storage_dir` | chosen at setup | Where the VM disks and build files go, inside a subfolder named `autorelabel`. |
| RHEL 10 ISO | `iso_path` | chosen at setup | Your RHEL 10 DVD image. |
| Networks (management) | `mgmt_subnet` | `192.168.250.0/24` | The management network autorelabel uses to prepare and grade the lab. |
| Networks (lab) | `lab_subnet_libvirt` | `172.25.250.0/24` | The lab network, with libvirt. |
| (command line only) | `lab_subnet_virtualbox` | `192.168.60.0/24` | The lab network, with VirtualBox. |
| (command line only) | `provider` | chosen at setup | The hypervisor: `libvirt` or `virtualbox`. |
| (command line only) | `code_server` | `true` | Whether RHCE exams include VS Code in the browser. |

## When a change takes effect

> **I changed the scoring (or the warnings, or downtime). Does my current exam change?**
> No. An exam keeps the scoring, warnings, difficulty display and downtime rule it was created with, so a setting can't change the rules halfway through. New exams and practice sessions use the new values.

> **I changed the profile. What happens to the lab?**
> The next exam notices that the lab was built for the other profile and rebuilds it, which takes a little longer once.

> **Can I move the RHEL 10 ISO?**
> Only if you update this setting too. The utility server reads its software repositories straight from the ISO every time the lab starts, so the ISO has to stay where the setting points. With libvirt, the VM user also needs permission to read it in its new place; the doctor checks this.

> **Can I change the lab storage directory?**
> Choose it once, at setup. The lab, the box and the downloaded content all live there, and the libvirt storage pool points at it. To move it, run `./autorelabel uninstall` (which also removes your settings and history), then run `./autorelabel` again and choose the new location.

> **One of the networks clashes with mine. What do I do?**
> The doctor tells you when a lab network overlaps a network your computer already uses (a VPN, a home network, a container network). Pick a free private subnet, then destroy the lab from **Lab and box** on the home screen, so the next exam builds it with the new network.

> **How do I switch between libvirt and VirtualBox?**
> Change `provider` with `./autorelabel config provider=virtualbox` (or `libvirt`). Each hypervisor needs its own box: the next exam offers to build it, or run `./autorelabel box build`. Both hypervisors can be installed together, but never run VirtualBox VMs and KVM VMs at the same time. If you switch often, `AUTORELABEL_WORKSPACE` keeps two completely separate setups; see the [command reference](07-commands.md#environment-variables).

## Changing settings from the command line

```bash
./autorelabel config                              # show every setting
./autorelabel config scoring=strict               # change one
./autorelabel config profile=standard show_difficulty_during_exam=true
./autorelabel config warnings_minutes=45,15,5     # lists are comma-separated
```

True/false settings accept `true`, `false`, `yes`, `no`, `on`, `off`, `1` and `0`. An unknown key, or a provider, profile or scoring value that doesn't exist, is refused and nothing is saved. Other values aren't checked here, so type subnets and paths carefully; the doctor checks them afterwards.
