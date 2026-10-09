#!/usr/bin/env bash
# Which users the grader expects where (the candidate's list is on control).
install -d /etc/autorelabel
printf 'AR_DEV=amira\nAR_DEV=bruno\nAR_MGR=chiara\nAR_MGR=dmitri\n' > /etc/autorelabel/vault-users
