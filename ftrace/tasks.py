#!/usr/bin/python

# Copyright 2015 Huawei Devices USA Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Authors:
#       Chuk Orakwue <chuk.orakwue@huawei.com>

"""
    TaskState: Possible task states from linux/sched.h
    Task: Runnable thread (process) executed on CPU.
"""
from six import integer_types
import matplotlib.pyplot as plt

class task():
    __slots__ = ('name', 'pid', 'prio', 'tgid', 'ppid',
            'sched_latency_ts', 'sched_latency', 'sleep_ts', 'sleep_duration',
            'wakers', 'wakeds')
    def __init__(self, name, pid, tgid=None, ppid=None, prio=None):
        pid = int(pid) if pid else pid
        prio = int(prio) if prio else prio
        try:
            tgid = int(tgid)
        except:
            tgid = tgid

        self.name = name
        self.pid = pid
        self.prio = prio
        self.tgid = tgid
        self.ppid = ppid
        self.sched_latency_ts = []
        self.sched_latency = []
        self.sleep_ts = []
        self.sleep_duration = []
        self.wakers = {}
        self.wakeds = {}

    def __repr__(self):
        #print(self.name, self.pid, self.prio, self.tgid, self.ppid)
        return "Task(name={:>16}, pid={:>8}, tgid={:>8})".format(
        self.name, self.pid, self.tgid,
        )

    def __eq__(self, other):
        """
        Compare by PID only. Prority is subject to change (dynamically)
        as is task name (post-fork).
        """
        if isinstance(other, task):
            return True if other.pid == self.pid else False
        elif isinstance(other, integer_types):
            return True if other == self.pid else False

        raise ValueError('{type} not supported'.format(type(other)))

    def __hash__(self):
        # IMPORTANT: Don't hash by name or priority
        # as those are subject to change in runtime
       return hash((self.pid))

    def affinity(self):
        """Return affinity if any, None otherwise"""
        try:
            return int(self.name.split('/')[-1][0])
        except:
            return

    def slot_wake(self):
        self.wakers = dict(sorted(self.wakers.items(), key = lambda x:x[1], reverse=True))
        self.wakeds = dict(sorted(self.wakeds.items(), key = lambda x:x[1], reverse=True))

    def add_sched_latency(self, ts, duration):
        self.sched_latency_ts.append(ts)
        self.sched_latency.append(duration)

    def show_sched_latency(self):
        l = len(self.sched_latency_ts)
        for i in range(l):
            print("{:>10.6f}s {:>10}us".format(self.sched_latency_ts[i], self.sched_latency[i]))
    def avg_sched_latency(self):
        if len(self.sched_latency):
            return round(sum(self.sched_latency) / len(self.sched_latency), 3)
        else:
            return 0

    def max_sched_latency(self):
        if self.sched_latency:
            return max(self.sched_latency)
        else:
            return 0

    def plot_sched_latency(self):
        plt.plot(self.sched_latency_ts, self.sched_latency, 'bx')
        plt.show()

    def add_sleep_ts(self, ts, duration):
        self.sleep_ts.append(ts)
        self.sleep_duration.append(duration)

    def show_sleep_ts(self):
        l = len(self.sleep_ts)
        for i in range(l):
            print("{:>10.6f}s {:>10}us".format(self.sleep_ts[i], self.sleep_duration[i]))

    def plot_sleep_ts(self):
        plt.plot(self.sleep_ts, self.sleep_duration, 'bx')
        plt.show()

    def add_waker(self, waker):
        if waker not in self.wakers:
            self.wakers[waker] = 0
        self.wakers[waker] = self.wakers[waker] + 1

    def add_waked(self, waked):
        if waked not in self.wakeds:
            self.wakeds[waked] = 0
        self.wakeds[waked] = self.wakeds[waked] + 1

class tasks(dict):
    def __init__(self):
        pass

    def addtask(self, task):
        self[task.pid] = task
    def showall(self):
        for k in self:
            print(k, self[k])


##normal scheduling policies
##    range: 0
##    (SCHED_OTHER, SCHED_IDLE, SCHED_BATCH)
##
##real-time policies
##    range: 1(low) to 99(high)
##    (SCHED_FIFO, SCHED_RR)
##
##PRIORITY = 20 + NICE
##NICE : -20 (high) to (20)
