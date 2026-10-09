## ansible-vault rekey

```bash
cd ~/ansible
echo '{{new}}' > salaries-pass.txt && chmod 0600 salaries-pass.txt
ansible-vault rekey salaries.yml --new-vault-password-file salaries-pass.txt
#   Vault password: {{old}}            (the current one, asked interactively)
ansible-vault view salaries.yml --vault-password-file salaries-pass.txt
```

Without `--new-vault-password-file`, rekey asks for the new password twice.

References: `ansible-vault rekey --help`.
