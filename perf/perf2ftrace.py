#! /usr/bin/env python
#-*- coding: utf8 -*-

import os
import re
import sys
 
def pr_err(*a):
    # Here a is the array holding the objects
    # passed as the argument of the function
    print(*a, file=sys.stderr)



# 打印的时候统一用该格式，这样可以python正则匹配每句log
# sudo perf script -F comm,tid,pid,cpu,time,event,trace > perf.script



thread_map = {}

# build thread map
# perf script的输出log里有一些线程名字丢了，有一些pid丢了，在输出ftrae log时候根据历史log修复下
# demo:
#           :-1    -1/-1    [015] 327083.028577:       sched:sched_switch: prev_comm=sh prev_pid=2377869 prev_prio=120 prev_state=X ==> next_comm=swapper/15 next_pid=0 next_prio=120 
with open("perf.script") as f:
    for line in f:
        #swapper     0/0     [004] 320543.563698:       sched:sched_switch: prev_comm=swapper/4 prev_pid=0 prev_prio=120 prev_state=R ==> next_comm=perf next_pid=2134363 next_prio=120
        ret = re.findall("(\S+)\s+(\S+)\/(\S+)\s+\[(\d+)\]\s+(\S+)\s+(\S+)([\S+\s+]+)\n", line)
        if ret:
            comm, tid, pid, cpu, time, event, trace = ret[0]
            if comm != "-1" and tid != "-1" and pid != "-1":
                thread_map[pid] = [pid, comm]


#for k in thread_map:
#    print(k, thread_map[k])


# 修复log里的pid和comm丢失
def get_tid_from_trace(trace):
    ret = re.findall("prev_comm=.{0,16} prev_pid=(\S+) prev_prio=\d+ prev_state=\S+ ==>[\S+\s+]+", trace)
    if ret:
        return ret[0]
    else:
        pr_err("get_tid_from_trace {} failed!".format(trace))


# output ftrace log
with open("perf.script") as f:
    transfer_failed_line = 0
    for line in f:
        #print(line)
        #swapper     0/0     [004] 320543.563698:       sched:sched_switch: prev_comm=swapper/4 prev_pid=0 prev_prio=120 prev_state=R ==> next_comm=perf next_pid=2134363 next_prio=120
        ret = re.findall("(^.{0,16})\s+(-?\d+)\/(-?\d+)\s+\[(\d+)\]\s+(\S+)\s+(\S+)([\S+\s+]+)\n", line)
        #print(ret)
        if ret:
            comm, pid, tid, cpu, time, event, trace = ret[0]
            vaild_log = 0; error_log = 0
            #print(comm, tid, pid, cpu, time, event, trace)
            if re.findall("sched_switch", event):
                event = "sched_switch:"
                vaild_log = 1
            elif re.findall("sched_waking", event):
                event = "sched_waking:"
                vaild_log = 1
            if vaild_log:
                if tid == "0":
                    pid = "-------"
                if tid == "-1":
                    tid = get_tid_from_trace(trace)
                    error_log = 1
                if pid == "-1" or comm == ":-1":
                    comm, pid = thread_map[tid]
                    error_log = 1
                new_log = " {:>16}-{:<8} ({:>7}) [{}] ..... {} {} {}".format(comm, tid, pid, cpu, time, event, trace)
                if error_log:
                    pr_err("\nfix errorlog\n{}to\n{}\n".format(line, new_log))
                print(new_log)
        else:
            pr_err("Unrecognized line:{}".format(line))
            transfer_failed_line = transfer_failed_line + 1
    pr_err("Transfer failed line: {}".format(transfer_failed_line))






