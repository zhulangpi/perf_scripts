#! /usr/bin/env python
#-*- coding: utf8 -*-

import os
import re
import sys
 
def pr_err(*a):
    # Here a is the array holding the objects
    # passed as the argument of the function
    print(*a, file=sys.stderr)


with open("perf.script") as f:
    for line in f:
        #print(line)
        #swapper     0/0     [004] 320543.563698:       sched:sched_switch: prev_comm=swapper/4 prev_pid=0 prev_prio=120 prev_state=R ==> next_comm=perf next_pid=2134363 next_prio=120
        ret = re.findall("(\S+)\s+(\d+)\/(\d+)\s+\[(\d+)\]\s+(\S+)\s+(\S+)([\S+\s+]+)\n", line)
        #print(ret)
        if ret:
            comm, tid, pid, cpu, time, event, trace = ret[0]
            #print(comm, tid, pid, cpu, time, event, trace)
            if re.findall("sched_switch", event):
                event = "sched_switch:"
            elif re.findall("sched_waking", event):
                event = "sched_waking:"
            if tid == "0":
                pid = "-------"
            print(" {:>16}-{:<8} ({:>7}) [{}] {} {} {}".format(comm, tid, pid, cpu, time, event, trace))
        else:
            pr_err("===================   ERROR LOG   =====================")
            pr_err(line)
            pr_err("===================   ERROR LOG   =====================")








