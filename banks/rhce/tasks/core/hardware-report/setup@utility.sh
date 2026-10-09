#!/usr/bin/env bash
install -d -m 0755 /var/www/html/ansible/files
cat > /var/www/html/ansible/files/hwreport.empty <<'TXT'
# Hardware report
HOST=inventory host name
MEMORY=total memory in MB
BIOS=bios version
DISK_A_SIZE=disk a size
DISK_B_SIZE=disk b size
DISK_C_SIZE=disk c size
TXT
chmod 0644 /var/www/html/ansible/files/hwreport.empty
restorecon -R /var/www/html/ansible/files
