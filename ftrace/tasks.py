#!/usr/bin/python

"""
    TaskState: Possible task states from linux/sched.h
    Task: Runnable thread (process) executed on CPU.
"""
from six import integer_types
import matplotlib.pyplot as plt
from common import ts2us
import numpy as np
import sys

class task():
    __slots__ = ('name', 'pid', 'prio', 'tgid', 'ppid',
            'sched_latency_ts', 'sched_latency', 'sleep_ts', 'sleep_duration',
            'wakers', 'wakeds', 'run_period_ts', 'run_period', 'sched_latency_in_period',
            'runtime_in_period', 'i')
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

        # 一次运行周期定义为: 线程T0时刻被唤醒，T1时刻开始运行，T2时刻再次sleep，运行周期 = T2 - T0
        self.run_period_ts = [] # T0
        self.run_period = [] # T2 - T0
        self.sched_latency_in_period = [] # runable time in period. T2 - T0这段时间内的调度延迟
        self.runtime_in_period = [] # T2 - T0 这段时间内的实际运行时间。这个值越高，代表线程会连续运行的时间越长。

        self.i = 0

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

    def max_sched_latency_ts(self):
        max_sdl = self.max_sched_latency()
        if max_sdl:
            idx = self.sched_latency.index(max_sdl)
            return self.sched_latency_ts[idx]
        else:
            return 0;

    def plot_sched_latency(self):
        plt.plot(self.sched_latency_ts, self.sched_latency, 'bx')
        plt.show()

    def calc_runtime(self):
        for t,sl in zip(self.run_period, self.sched_latency_in_period):
            if t:
                self.runtime_in_period.append(t - sl)
            else:
                self.runtime_in_period.append(0)


    def avg_runtime(self):
        if len(self.runtime_in_period):
            return round(sum(self.runtime_in_period) / len(self.runtime_in_period), 3)
        else:
            return 0

    def max_runtime(self):
        if self.runtime_in_period:
            return max(self.runtime_in_period)
        else:
            return 0

    def show_runtime(self):
        l = len(self.run_period_ts)
        for i in range(l):
            print("{:<10} {:>10} {:>10} {:>10}us".format(self.run_period_ts[i], self.run_period[i], self.sched_latency_in_period[i], self.runtime_in_period[i]))

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

    def append_run_period_ts(self, ts):
        self.run_period_ts.append(ts)

    def append_sched_latency_in_period(self, sl):
        self.sched_latency_in_period.append(sl)

    def add_sched_latency_in_period(self, sl):
        self.sched_latency_in_period[-1] = self.sched_latency_in_period[-1] + sl

    def append_run_period(self, ts):
        self.run_period.append(ts)

    def update_run_period(self, ts):
        self.run_period[-1] = ts2us(ts - self.run_period_ts[-1])

    # 以下两个函数 展示了线程 每个运行周期中，调度延迟的时间和占比
    # 比如说，线程A 在T0时刻被唤醒，在T1时刻结束运行，T1-T0称作一次“运行周期”，这个时间短内的调度延迟占比越大，可能表明这次pipleline被调度影响的严重。
    def show_sched_latency_each_period(self):
        percent = []
        length = len(self.run_period_ts)
        if length == 0:
            return
        for i in range(length):
            if self.run_period[i] == 0: # 可能log已经结束，导致waking没有对应的switch_out
                continue
            percent.append(self.sched_latency_in_period[i] / self.run_period[i])
        #for i in range(length):
        #    print("{:>6.6f} {:>8} {:>3.3f}".format(self.run_period_ts[i], self.sched_latency_in_period[i], percent[i]))
        print("avg:{:>10.01f} max:{:>10.0f} 99%:{:>10.0f}".format(sum(self.sched_latency_in_period) / length, max(self.sched_latency_in_period), np.percentile(self.sched_latency_in_period, 99)))

    def plot_sched_latency_each_period(self):
        percent = []
        print(len(self.sched_latency_in_period), len(self.run_period), len(self.run_period_ts))
        for i in range(len(self.sched_latency_in_period)):
            percent.append(self.sched_latency_in_period[i] / self.run_period[i])

        fig, ax1 = plt.subplots()
        ax1.set_xlabel('timestamp')
        ax1.set_ylabel('sched latency each period')
        ax1.tick_params(axis='y')
        ax1.plot(self.run_period_ts, self.sched_latency_in_period, 'bx', label='sched latency each period')
        plt.legend(bbox_to_anchor=(1, 1), fontsize=10, frameon=True)
        ax2 = ax1.twinx()
        ax2.set_ylabel('percent of sched latency each period')
        ax2.tick_params(axis='y')
        ax2.set_ylim(0, 1)
        ax2.plot(self.run_period_ts, percent, 'r.', label='percent of sched latency each period')
        plt.legend(bbox_to_anchor=(1, 0.9), fontsize=10, frameon=True)
        plt.title(' ')
        plt.show()

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
