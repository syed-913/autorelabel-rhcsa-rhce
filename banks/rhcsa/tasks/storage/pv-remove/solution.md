## Remove a physical volume

```bash
pvs -o pv_name,vg_name,pv_used        # the second PV is unused (PV Used = 0)
vgreduce {{vg}} {{lab.node1.disk2}}N  # if it held data: pvmove {{lab.node1.disk2}}N first
pvremove {{lab.node1.disk2}}N
pvs; vgs {{vg}}
```

References: RHEL 10 *Configuring and managing logical volumes*; `man vgreduce`, `man pvremove`.
