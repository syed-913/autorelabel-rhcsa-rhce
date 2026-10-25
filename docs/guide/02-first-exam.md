# Your first exam

This page walks through one complete RHCSA exam, from the home screen to your results. An RHCE exam follows the same steps; the differences are noted where they matter.

## The home screen

Start autorelabel with `./autorelabel`. The home screen lists what you can do, with the most likely choice at the top.

<p align="center"><img src="../media/home.png" width="760" alt="The home screen: new RHCSA or RHCE exam, practice, history, lab and box, doctor, settings"></p>

| Choice | What it does |
|---|---|
| **New RHCSA exam** / **New RHCE exam** | Draws a new 20-task exam and prepares the lab for it. |
| **Practice RHCSA / RHCE** | Untimed practice on tasks you choose. See [Practice mode](06-practice.md). |
| **Progress and history** | Your past scores and your weakest objectives so far. |
| **Lab and box** | The state of the box and the lab VMs; rebuild the box or destroy the lab. |
| **Doctor** | Checks your computer again (`d` from anywhere on the home screen). |
| **Settings** | See [Settings](08-settings.md) (`s`). |
| **Uninstall (how to)** | Shows the commands that remove everything. |

When a session is already open, the first line offers to return to it, for example **Return to your exam** or **Results of your last exam**.

You can also skip the home screen: `./autorelabel rhcsa` (or `rhce`) opens autorelabel and starts a new exam right away.

## Preparing the lab

Choose **New RHCSA exam**. autorelabel draws 20 tasks from the bank (6 easy, 8 medium and 6 hard, with every objective domain represented), fills in their details (user names, sizes, ports, passwords) at random, and prepares the lab. The screen shows each stage:

1. **The first time only:** the lab VMs are created and set up, then saved as a clean snapshot. This takes noticeably longer than later exams.
2. **Restoring a clean lab** from that snapshot, so no earlier exam leaves anything behind.
3. **Preparing this exam's starting point:** each task sets up what it needs, such as a broken service to fix, a disk to partition or a user that already exists.
4. **Saving the exam starting point**, which is what *Retake* and *Reset to exam start* go back to.

After the first time, preparing an exam takes about 2 to 5 minutes. The clock has not started yet.

> **Will two exams ever be the same?**
> Rarely. Tasks are drawn at random within the blueprint, their details are randomised, and the draw gives more weight to objectives you haven't practised in your recent attempts. If you want the same exam again, use *Retake* from the results screen.

> **What is the "utility server" I see while the lab starts?**
> A VM that plays the role of the support server in the real exam. It serves the RHEL 10 software repositories from your DVD, DNS for `lab.example.com`, time (NTP), NFS shares and the Flatpak repository. You use it from the nodes but never change it. See [The lab](04-the-lab.md).

## The instructions

When the lab is ready, the instructions appear. Read them: they are what the real exam gives you before you start.

- **Time and points:** 180 minutes (240 for RHCE), 20 tasks, 300 points, 210 to pass.
- **The reboot rule:** every node is rebooted before grading, so only what survives a reboot counts.
- **Your systems:** a table with each node's name, full host name, address and **root password**.
- **The network:** the subnet, gateway, DNS server and the utility server's name.
- **How to work**, and the **rules**: don't change the `mgmt0` interface, the `vagrant` account or its sudo rule, and don't touch the utility server.

> **Why is node2's root password "unknown"?**
> Because resetting it is one of your tasks, just as in the real exam. You interrupt node2's boot (`rd.break`), set the new password the task asks for, and make sure SELinux relabels the file system on the next boot (`touch /.autorelabel`). That last step is where this project's name comes from.

> **Can I see the instructions again during the exam?**
> Yes. Press `i` on the exam screen at any time, or run `./autorelabel exam tasks` in a terminal.

Press **Start the exam**. The clock starts now.

## Working on the tasks

<p align="center"><img src="../media/exam.png" width="880" alt="The exam screen: the 20 tasks, the countdown, task 18 open, and the nodes"></p>

The exam screen shows the task list on the left, the selected task on the right, the time left at the top right and your nodes at the bottom. Move through the tasks with the arrow keys. Each task names the node it runs on.

You do the work in your own terminals, in two ways:

- **SSH**, for most tasks: `./autorelabel ssh node1` logs you in as root over the lab network. Type the root password from the instructions when SSH asks for it. In an RHCE exam, `./autorelabel ssh control` logs you in as `student` (with the `student` password), which is where you work.
- **The serial console**, for tasks that need it (GRUB, `rd.break`, emergency mode, or a node without network): `./autorelabel console node1`. Press Enter for a prompt, and `Ctrl+]` to leave.

You can also open both from the exam screen: select a node in the bottom bar with ←/→, then press `s` for SSH or `c` for the console. The exam screen returns when you exit.

> **Why can't I SSH to node1 or node2 at the start of an RHCSA exam?**
> node1 starts without a network configuration on its lab interface, and configuring it is one of the tasks. Until you do, the console is the only way in: log in as `root` with the password from the instructions (the console prints it when you connect, and it is shown under the task too). node2 has a network, but its root password is unknown until you reset it through the console. That is how a real RHCSA exam usually begins: the first few tasks open the door to everything else.

Mark your progress with `d` (done) and `f` (flag, for tasks you want to come back to). The marks are only for you: grading ignores them.

## Keeping an eye on the time

The clock at the top right turns yellow with 10 minutes left and red with 2 minutes left. You also get warnings at 30, 10, 5 and 1 minutes left, in three places: a notification on the exam screen, a message inside every SSH session on the nodes, and a desktop notification.

If you prefer to see the time while you work in other windows, run this in a small spare terminal:

```bash
./autorelabel exam timer
```

It shows the time left in large digits. `--compact` shows a single line, and `--once` prints the time once, for a tmux or shell status line.

> **What happens if I close autorelabel, or my laptop goes to sleep?**
> The exam keeps running in the background. A small background process, the proctor, keeps time, sends the warnings and grades the exam at zero, whether autorelabel is open or not. Time while your computer sleeps or after a crash is not counted, so a closed lid doesn't eat into your exam (you can turn this off in [Settings](08-settings.md) for a stricter clock). Run `./autorelabel` again to return to it.

## Finishing

The exam ends when the time runs out, or when you press `x` (Submit) and confirm. From that moment the lab is frozen: the VMs are paused and you can no longer change anything.

Grading then runs in three phases, shown on the grading screen:

1. **Checking your work before the reboot.** This pass doesn't count. It is only used to find work that disappears with the reboot.
2. **Rebooting every exam node**, cleanly, and waiting for each one to come back.
3. **Grading after the reboot.** This is the pass that counts.

Grading usually takes a few minutes. If a node doesn't come back, autorelabel reads its serial console and tells you why. [Grading and results](05-grading-and-results.md) explains every phase.

## Your results

<p align="center"><img src="../media/results.png" width="880" alt="The results: 258 of 300, PASS, points per difficulty and domain, and every check of task 18"></p>

The results screen shows:

- your score out of 300 and **PASS** or **FAIL** (the pass mark is 210),
- your points per difficulty and per objective domain,
- every task with ✔ (full points), ◐ (partial points) or ✘ (no points),
- for the selected task, every check with its result, and a note on any check that **worked before the reboot, not after**.

Press `v` to read the selected task's solution, with references to Red Hat's documentation. Press `t` to **retake** the same exam from its starting point. Press Escape to go home.

> **What should I do after my first exam?**
> Read the solution of every task that wasn't ✔, even the ones you passed partly; the persistence notes are the most useful part. Then practise the weak ones in [Practice mode](06-practice.md), and check **Progress and history** on the home screen, which lists your weakest objectives across all your attempts.
