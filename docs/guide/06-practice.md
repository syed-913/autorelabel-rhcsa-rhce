# Practice mode

Practice mode is for learning, not for testing yourself. You pick the tasks, there is no clock, you can check your work as often as you like, and the solution is one key away.

## Starting a practice session

On the home screen choose **Practice RHCSA: pick tasks** (or **Practice RHCE**). The list shows every task in the bank, grouped by objective domain, with its difficulty.

- Press **Space** to select or deselect a task.
- Press **Enter** to start.
- You can pick up to 10 tasks per session.

autorelabel then prepares the lab, as for an exam, and shows the instructions. Press **Start**, and the exam screen opens without a clock.

> **Can I practise while an exam is running?**
> No. Finish or abandon the exam first. There is only one lab, and practice would change it under your exam.

## What is different from an exam

| | Exam | Practice |
|---|---|---|
| Tasks | 20, drawn by the blueprint | the ones you picked (up to 10) |
| Clock | 180 or 240 minutes, enforced | none |
| Difficulty shown | only if turned on in Settings | always |
| Check your work early | no | yes, with or without a reboot |
| Solutions | after grading | at any time |
| Final grading | at the end, after a reboot | when you finish, after a reboot |

Only the tasks you picked change the lab. If you didn't pick the task that configures node1's network, node1 has a working network and you can SSH to it. If you didn't pick the repositories task, the repositories already work, so a single storage task is never blocked by an unrelated one. In an RHCE practice session, the Ansible configuration, the managed nodes' SSH access and the collections are also prepared for you, unless one of your tasks is about them.

## Keys

The exam screen works exactly as described in [The exam screen](03-exam-screen.md), with three extra keys:

| Key | What it does |
|---|---|
| `k` | **Check now.** Runs every check of your tasks on the nodes as they are, without a reboot, and shows which ones pass. |
| `r` | **Check after a reboot.** Reboots the nodes first, then checks, the way final grading does. This is how you find work that isn't persistent. |
| `v` | **Solution** for the selected task, with references to Red Hat's documentation. |

These checks are unofficial: they don't end the session and aren't saved to your history. When you are done, press `x` to finish. The session is then graded like an exam, with a reboot, and the results screen opens.

> **Why does the score of a practice session say "out of 300"?**
> To make it comparable with an exam. A practice set worth, say, 45 points is scaled to the 300-point scale, and PASS or FAIL is decided against 210 the same way.

> **Does `r` change my work?**
> Only in the way a reboot does: anything that wasn't persistent is gone afterwards, which is what it is there to show you. Your saved configuration stays.

## Tasks you only find in practice

Two tasks never appear in an exam, because they break a node in a way that would block the rest of the exam:

- **Recover a locked and expired root account** on node1, through the boot loader.
- **Fix a node that always boots into emergency mode** because of a kernel argument, on node2.

They are still worth practising: both are about getting into a system you can't log in to.

## A routine that works

1. Take a full exam to find your weak areas. **Progress and history** on the home screen lists your weakest objectives.
2. Practise those areas: pick two or three related tasks, solve them, press `r`, read every failed check.
3. Read the solution even when you passed. The solutions point to the man pages and the Red Hat documentation behind each step. The man pages are what you will have in the real exam, so it pays to know where the answer is in them.
4. Retake the exam from its results screen (`t`) a few days later, or start a new one.
