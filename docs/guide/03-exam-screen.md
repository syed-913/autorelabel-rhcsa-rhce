# The exam screen

This page is a reference for everything on the exam screen: its parts, its keys, the node actions and the warnings it can show.

## The parts of the screen

| Part | What it shows |
|---|---|
| **Header** | The exam type, the number of tasks, how many you marked done, and the time left. The clock turns yellow at 10 minutes and red at 2 minutes. |
| **Warning banner** | Appears only when something needs your attention, such as the grader losing access to a node (see below). |
| **Task list** (left) | The 20 tasks, with your marks: ✔ for done and ⚑ for flagged. If *Show task difficulty* is on in Settings, each task also shows easy, medium or hard. |
| **Task view** (right) | The selected task: its points, the node it runs on and its full text. Console-only tasks also show how to open the console and how to log in. |
| **Node bar** (bottom) | Every node with its power state (● running, paused or shut off). The selected node is highlighted. |
| **Footer** | The main keys. |

## Keys

| Key | What it does |
|---|---|
| ↑ / ↓ | Move through the task list. |
| ← / → | Select a node in the node bar. |
| `s` | Open SSH to the selected node. You return to this screen when you log out. |
| `c` | Open the selected node's serial console. `Ctrl+]` brings you back. |
| `n` | The node actions menu (below). |
| `d` | Mark the selected task as done (press again to clear). |
| `f` | Flag the selected task (press again to clear). |
| `i` | Show the instructions again, including the root passwords. |
| `x` | Submit: end the exam now and grade it. You are asked to confirm. |
| Escape | Go to the home screen. A timed exam keeps running. |

In [practice mode](06-practice.md) three more keys work: `k` checks your work now, `r` checks it after rebooting the nodes, and `v` shows the selected task's solution. They do nothing during an exam.

> **Do the done and flag marks affect my score?**
> No. They exist only to help you keep track. Grading looks at the state of the nodes, never at your marks.

> **Why does the console show a blank screen?**
> A serial console only prints when something writes to it. Press Enter and the login prompt (or the GRUB menu, or an emergency shell) appears. If the node is booting, wait a moment and press Enter again.

## Node actions

Press `n` to open the actions for the selected node:

| Action | When to use it |
|---|---|
| **SSH as root** (as `student` on the RHCE control node) | The same as `s`. |
| **Serial console** | The same as `c`. Use it for GRUB, `rd.break` and emergency mode. |
| **Power on** | The node is shut off, for example after you ran `poweroff` on it. |
| **Reset** | The node hangs. This is a hard reboot, like pressing a computer's reset button: anything not yet written to disk is lost, but your saved configuration stays. |
| **Reset to exam start** | You broke the node beyond repair. This puts back the node exactly as it was when the exam started. **All your work on that node is lost**, and the clock keeps running. |

> **Is "Reset to exam start" counted against me?**
> It doesn't cost points by itself, but it is recorded and shown in your results as an incident, so you can see later where the time went. Your work on the other nodes is not touched.

> **What is the difference between Reset and rebooting from inside the node?**
> `reboot` inside the node is a clean shutdown, and it is what the grader does too. Use it whenever the node responds. Reset is for a node that no longer responds at all.

## The warning banner

About every two minutes, the proctor checks that the grader can still log in to each node. If it can't, a warning banner appears on the exam screen and a message is sent to your SSH sessions:

> The grader can no longer reach node1: revert changes to mgmt0, the vagrant account, sshd or sudo, or those tasks will score 0.

> **What are `mgmt0` and the `vagrant` account?**
> Every lab VM has two network interfaces. The lab interface is yours: tasks ask you to configure it. `mgmt0` is a separate management interface that autorelabel uses to prepare the lab and to grade it, together with the `vagrant` account and its sudo rule. The real exam has a similar arrangement that you never see. If you change `mgmt0`, remove the `vagrant` account, or break SSH or sudo in a way that locks it out, the grader can't check your work on that node, and its tasks score 0. The banner gives you time to undo the change.

## Leaving and coming back

Press Escape to go to the home screen. A timed exam keeps running while you are away, and the home screen offers **Return to your exam**. You can also quit autorelabel completely: the proctor keeps the time, sends the warnings, and locks and grades the exam at zero. Run `./autorelabel` (or `./autorelabel resume`) to return.

> **My computer restarted in the middle of an exam. Is it lost?**
> No. When you open autorelabel again, it notices the restart and offers **Resume your interrupted exam**. The lab starts again with your work as it was on disk, and the time your computer was off is not counted (unless you turned off *Forgive host downtime* in Settings).
