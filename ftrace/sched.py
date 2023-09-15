#! /usr/bin/env python
#-*- coding: utf8 -*-

from interval import Interval
from bisect import bisect_left, bisect
import re
from tasks import task, tasks
from common import pr_err

class sched_switch_event():
    __slots__ = ('prev_pid', 'prev_prio', 'prev_state', 'next_pid', 'next_prio')
    #__slots__ = ('line', 'prev_comm', 'prev_pid', 'prev_prio', 'prev_state', 'next_comm', 'next_pid', 'next_prio')
    def __init__(self, trace):
        ret = re.findall(
            "\s+prev_comm\=(.{0,16})\s+prev_pid\=(\d+)\s+prev_prio\=(\d+)\s+prev_state\=(\S+)\s+==>\s+next_comm\=(.{0,16})\s+next_pid\=(\d+)\s+next_prio\=(\d+)",
            trace)
        if ret:
#            self.line = []
            prev_comm, prev_pid, prev_prio, prev_state,\
            next_comm, next_pid, next_prio = ret[0]
            self.prev_pid = int(prev_pid)
            self.prev_prio = int(prev_prio)
            self.next_pid = int(next_pid)
            self.next_prio = int(next_prio)
            self.prev_state = prev_state
        else:
            print("parse failed {}".format(trace))
#    def __repr__(self):
#        return "{}".format(self.line)


class sched_waking_event():
    __slots__ = ('pid', 'prio', 'target_cpu')
    #__slots__ = ('line', 'comm', 'pid', 'prio', 'target_cpu')
    def __init__(self, trace):
        ret = re.findall("\s+comm\=(.{0,16}) pid\=(\d+) prio\=(\d+)[\s\S]+target_cpu\=(\d+)", trace)
        if ret:
#            self.line = []
            comm, self.pid, self.prio, self.target_cpu = ret[0]
            self.pid = int(self.pid)
            self.prio = int(self.prio)
            self.target_cpu = int(self.target_cpu)
        else:
            print("parse failed {}".format(trace))
#    def __repr__(self):
#        return "{}".format(self.line)

