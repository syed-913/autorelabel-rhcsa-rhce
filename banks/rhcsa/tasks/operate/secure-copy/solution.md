## Secure file transfer

```bash
# on node1
mkdir -p /srv/incoming
scp root@node2:/root/{{word}}-config.tar /srv/incoming/
rsync -av /opt/{{word}}-docs/ root@node2:/opt/{{word}}-docs/     # -a keeps modes, times, ownership
ssh root@node2 hostname > /root/node2-hostname.txt
```

(`rsync` must be installed on both sides.) `sftp root@node2` is the interactive alternative to scp.

**Classic mistake:** `scp -r` or `cp -r` without preserving attributes. Permissions and
timestamps differ from the source (`scp -p`, `rsync -a`, `cp -a` preserve them).

References: RHEL 10 *Securing networks* → OpenSSH (scp, sftp); `man rsync` (`-a`).
