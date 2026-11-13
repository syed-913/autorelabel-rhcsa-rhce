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
| `w` | Open the [Exam Desk](#the-exam-desk-the-exam-in-your-browser): the same exam in your browser, with terminals beside the tasks. |
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

## The Exam Desk: the exam in your browser

The Exam Desk shows the exam in one browser window: the tasks on the left, terminals and consoles to the nodes on the right, and the clock on top. It looks and works like an exam workstation, and you can use it next to this screen or on its own.

Open it with `w` on this screen, or run `./autorelabel desk` in a terminal. Your browser opens a page on your own computer that asks for a code. The code is shown in the dialog (or printed by the command); type it in once. It keeps anyone else, and any other web page, away from your shells.

| Part | What it does |
|---|---|
| The number grid | Every task, with `✓` for done and `⚑` for review. Select one to read it. |
| Mark done, Mark for review | The same marks as `d` and `f` here. They never affect your score. |
| The node tabs | One per node, with its state in words: running, off, rebooting, unreachable. |
| New shell | SSH to the node, as root (on RHCE's control node, as student). You type the password, as in the exam. |
| Open console | The node's serial console, for the tasks without a network and for interrupting the boot. |
| Split | Two terminals side by side. On a wide screen this is the default. |
| Reset node | Back to how the node was when the exam started. Everything you changed on it is lost, and you are asked first. |
| Open VS Code | RHCE only: VS Code in the browser, on the control node. |
| End exam | The same as `x` here. You are asked first. |

**Your shells survive the tab.** Close it, reload it or open the address in a second window: the same shells come back with their output. They end when you quit autorelabel (or stop `./autorelabel desk`); the exam and the clock carry on.

**At time up the terminals become read-only.** You can still read and scroll them; typing goes nowhere, here and on the server. Then grading reboots every node, as always.

**Full screen** gives the page the whole screen. In Chrome, Chromium and Edge it also gives the shells the keys a browser normally keeps for itself, such as Ctrl+W (Vim's window key), Ctrl+T and Ctrl+N. Firefox keeps them: there, Ctrl+W closes the tab, but your shells keep running, and opening the address again brings them back. The page asks before you close it while the exam runs.

> **Do I need the Exam Desk?**
> No. It is another way to sit the same exam: this screen, SSH and the console all keep working, and you can switch between them at any time.

> **Why does the Exam Desk need a window at least 1100 pixels wide?**
> The tasks and the terminals sit side by side, as on the exam. In a narrower window the page says so, and your shells and the clock keep running.

