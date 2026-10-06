## Network services and sockets

```bash
systemctl enable --now httpd
ss -lntup | grep ':111'                         # rpcbind (and systemd itself, via the socket)
systemctl disable --now rpcbind.socket rpcbind.service
ss -lntup | grep ':111'                         # nothing
```

Socket-activated services have a `.socket` unit that keeps the port open and starts the service
on demand. Stopping only the `.service` leaves the port listening.

References: RHEL 10 *Using systemd unit files*; `man systemd.socket`, `man ss`.
