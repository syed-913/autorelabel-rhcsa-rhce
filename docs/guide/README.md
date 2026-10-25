# autorelabel user guide

This guide explains how to install autorelabel, take an exam, read your results and get help when something goes wrong. The pages are meant to be read in order the first time. After that, use them as a reference.

1. **[Installing](01-installing.md).** What each dependency is for, the first run, the setup questions and the box build.
2. **[Your first exam](02-first-exam.md).** From the home screen to your results, step by step.
3. **[The exam screen](03-exam-screen.md).** Every key, the node actions and the warnings you may see.
4. **[The lab](04-the-lab.md).** The virtual machines, their networks and accounts, and what the utility server provides.
5. **[Grading and results](05-grading-and-results.md).** What happens during the reboot, how points are calculated and what a persistence warning means.
6. **[Practice mode](06-practice.md).** Untimed drills on the tasks you choose, with checks you can run at any time.
7. **[Command reference](07-commands.md).** Every `./autorelabel` command, for people who prefer the command line or want to script it.
8. **[Settings](08-settings.md).** Every setting, what it changes and when the change takes effect.
9. **[Troubleshooting](09-troubleshooting.md).** The doctor's checks, common problems and how to report one.
10. **[Files and uninstalling](10-files-and-uninstall.md).** Everything autorelabel puts on your computer, and how to remove it.
11. **[FAQ](11-faq.md).** Short answers to the questions people ask most.
12. **[Exam objectives covered](12-objectives.md).** Every official objective line and its coverage.

## A few words you will meet often

These terms come up throughout the guide. Each page explains them again where they matter.

| Term | Meaning |
|---|---|
| **Node** | A virtual machine you work on during the exam, such as `node1`. |
| **Utility server** | A virtual machine that provides the lab's software repositories, DNS, time and file shares. You never change it. |
| **Box** | The RHEL 10 virtual machine image that every lab VM starts from. autorelabel builds it once from your ISO. |
| **Lab** | The set of VMs for one exam type: the utility server plus the nodes. |
| **Session** | One exam or practice attempt, with its tasks, clock and results. |
| **Proctor** | A small background process that keeps time, sends warnings and grades your exam when the time is up. |
| **Doctor** | The built-in check of your computer: `./autorelabel doctor`. |
| **Lab storage directory** | The folder where autorelabel keeps the VM disks and build files, inside a subfolder named `autorelabel`. |
| **Persistence** | Whether your configuration survives a reboot. Only persistent work earns points. |

> **Is there anything I should read before I start?**
> If your computer already has the tools from the README's [Requirements](../../README.md#requirements) section, go straight to [Installing](01-installing.md#the-first-run). If not, start at the top of that page.
