## Reading tally.sh

```bash
for n in "$@"; do                 # every argument, in order
  if (( n % 2 == 0 )); then       # even → add to the sum, print nothing
    total=$(( total + n ))
  else                            # odd → count it and print "odd: N" immediately
    odd=$(( odd + 1 ))
    echo "odd: $n"
  fi
done
echo "even sum: $total"
echo "odd count: $odd of $#"      # $# = number of arguments
```

For `tally.sh {{args}}` the odd numbers are printed first, in order, then the two summary lines.
Check yourself: `~/scripts/tally.sh {{args}} > ~/answers/tally.txt`.

References: `man bash` (ARITHMETIC EVALUATION, Special Parameters).
