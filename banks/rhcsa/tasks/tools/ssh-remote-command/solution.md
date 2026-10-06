## Remote commands over SSH

```bash
ssh root@node2 lsblk -o NAME,SIZE,TYPE > /root/node2-disks.txt
cat /root/node2-disks.txt
```

The command after the host name runs **remotely**; the redirection `>` is done by **your local
shell**, so the file lands on node1. (Quote it, `ssh node2 'cmd > file'`, to write on node2.)

References: `man ssh`.
