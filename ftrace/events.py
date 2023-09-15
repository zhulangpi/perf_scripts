#! /usr/bin/env python
#-*- coding: utf8 -*-

from interval import Interval
from bisect import bisect_left, bisect
import re
from tasks import task, tasks
from sched import sched_switch_event, sched_waking_event
from common import pr_err
from common import ts2us
import numpy as np
import plotly.express as px
import pandas as pd
#from multiprocessing import Process, Manager
import time
import sys

def calc_cpu_loading(elist, pid, c, time_interval, ts, loadings):
    currlist = []
    sumtime = 0
    t0 = time.time()
    print("start calc_cpu_loading of {}".format(c))
    for t in ts:
        if t + time_interval > ts[-1]:
            break
        runtime, currlist = elist.calc_runtime_timerange(pid, [c], [t, t + time_interval], currlist)
        loading = 100.0 * runtime / time_interval
        loadings.append(loading)
    print("end  calc_cpu_loading of {}\ncost {}s".format(c, time.time() - t0))
    #sys.exit(0)


class event:
    __slots__ = ('task', 'cpu', 'timestamp', 'eventtype', 'trace')

    def __init__(self, tsk, cpu, timestamp, eventtype, trace):
        self.task = tsk
        self.cpu = cpu
        self.timestamp = timestamp
        self.eventtype = eventtype

        if self.eventtype == "sched_switch":
            self.eventtype = "sched_switch"
            self.trace = sched_switch_event(trace)
        elif self.eventtype == "sched_waking":
            self.eventtype = "sched_waking"
            self.trace = sched_waking_event(trace)
        else:
            self.eventtype = "undefined event"
            self.trace = -1

    def __repr__(self):
        return "Event(type={} task={}, cpu={}, timestamp={:.06f}, trace={}".format(
        self.eventtype, self.task, self.cpu, self.timestamp, self.trace)


class eventlist(list):
    def __init__(self, iterable=None):
        self._timestamps = []
        if iterable:
            for item in iterable:
                self.append(item)

    def start(self):
        return self._timestamps[0]

    def end(self):
        return self._timestamps[-1]

    def duration(self):
        try:
            return Interval(start=self.start, end=self.end)
        except:
            return None

    def check_if_data_lost(self):
        prev_cpus = [-1] * 64 # assume that cpus_nr <= 64
        for e in self:
            if e.eventtype == "sched_switch":
                if prev_cpus[e.cpu] != -1:
                    if prev_cpus[e.cpu] != e.trace.prev_pid:
                        pr_err("error: discontinous data({}) at {}".format(e.trace, e.timestamp))
                prev_cpus[e.cpu] = e.trace.next_pid


    def __add_timestamp(self, obj):
        """Insert (sorted) object with timestamp attribute to timestamps list.
        """
        ts = obj.timestamp
        idx = bisect(self._timestamps, ts)
        self._timestamps.insert(idx, ts) # insert items sorted
        return idx

    def append(self, obj):
        """Append new event to list"""
        try:
            obj.timestamp
        except AttributeError:
            raise TypeError("Must have timestamp attribute")
        super(self.__class__, self).insert(self.__add_timestamp(obj), obj)

    def slice(self, interv, closed=None):
        """
        Returns list of objects whose timestamps fall
        between the specified interval.

        Parameters:
        -----------
        closed : string or None, default None
            Make the interval closed with respect to the given interval to
            the 'left', 'right', or both sides (None)
        """
        if interv is None:
            return self
        else:
            start, end = interv.lower_bound, interv.upper_bound

        left_closed, right_closed = False, False

        if closed is None:
            left_closed = True
            right_closed = True
        elif closed == "left":
            left_closed = True
        elif closed == "right":
            right_closed = True
        else:
            raise ValueError("Closed has to be either 'left', 'right' or None")

        idx_left = bisect_left(self._timestamps, start)
        idx_right = bisect(self._timestamps, end)

        if start in self._timestamps and not left_closed:
            idx_left = idx_left + 1
        if end in self._timestamps and not right_closed:
            idx_right = idx_right - 1

        left_adjust = idx_left < len(self)

        return eventlist(self[idx_left:idx_right]) if left_adjust else eventlist()

    def filter(self, cpu):
        elist = eventlist()
        for e in self:
            if e.cpu == cpu:
                elist.append(e)
        return elist

    # usage: calc_runtime_timerange(1, [0], [200,300])
    # this will calc task 1 running time on cpu0 between 200s-300s
    # currlist 代表cpu上当前运行着的任务的pid
    def calc_runtime_timerange(self, pid, cpulist, time_range, currlist = []):
        self = self.slice(Interval(time_range[0], time_range[1]))
        runtime = [-1] * len(cpulist)
        switchin_time = [0] * len(cpulist)
        sumtime = 0
        if currlist:
            tmplist = currlist
        else:
            tmplist = [0] * len(cpulist)
        for e in self:
            if e.eventtype == "sched_switch":
                if e.cpu not in cpulist:
                    continue
                cpulist_idx = cpulist.index(e.cpu)
                if e.trace.next_pid == pid:
                    switchin_time[cpulist_idx] = e.timestamp
                tmplist[cpulist_idx] = e.trace.next_pid
                if runtime[cpulist_idx] == -1:
                    if e.trace.prev_pid == pid:
                        runtime[cpulist_idx] = e.timestamp - time_range[0]
                    else:
                        runtime[cpulist_idx] = 0
                    continue
                if e.trace.prev_pid == pid:
                    runtime[cpulist_idx] = runtime[cpulist_idx] + e.timestamp - switchin_time[cpulist_idx]
                    switchin_time[cpulist_idx] = 0
        for idx, rt in enumerate(runtime):
            if rt == -1:
                runtime[idx] = 0

        for idx, st in enumerate(switchin_time):
            if st:
                runtime[idx] = runtime[idx] + time_range[1] - st
        if currlist:
            for idx,cur in enumerate(currlist):
                if cur == pid and runtime[idx] == 0:
                    runtime[idx] = time_range[1] - time_range[0]

        for idx, rt in enumerate(runtime):
            print("running time {} on cpu{} ".format(round(rt,6), cpulist[idx]))
        print("total running time {} between {}-{}".format(sum(runtime), time_range[0], time_range[1]))
        return (sum(runtime), tmplist)


    # usage: calc_cpus_loading([0,1,2], 0.1, [200,300])
    # this will calc cpu loading of cpu 0,1,2 between time of [200, 300]s, interval of time is 0.1s
    def calc_cpus_loading(self, pid, cpulist, time_interval):
        if time_interval < 0.1:
            print("too small interval will meaningless")

        workers = [ [] for x in  range(len(cpulist))]
        ts = np.arange(self.start(), self.end(), time_interval)
        loadings = list(range(len(cpulist)))

        for idx,c in enumerate(cpulist):
            #loadings[idx] = Manager().list()
            loadings[idx] = list()

        parallel = 1
        end = len(cpulist)
        for i in range(0, end, parallel):
            if i + parallel > end:
                j = end
            else:
                j = i + parallel
            for idx in range(i, j):
                c = cpulist[idx]
                tmpelist = self.filter(c)
                calc_cpu_loading(tmpelist, pid, c, time_interval, ts, loadings[idx])
#                workers[idx] = Process(target = calc_cpu_loading, args=(tmpelist, pid, c, time_interval, ts, loadings[idx]))
#                workers[idx].start()

#            for idx in range(i, j):
#                workers[idx].join()
#                workers[idx].terminate()

        for idx in range(len(loadings)):
            loadings[idx] = list(loadings[idx])

        for l in loadings:
            print(l)

        keys = cpulist
        df = pd.DataFrame(dict(zip(keys, loadings)))
        df['sum'] = df.apply(lambda x: x.sum() / len(cpulist), axis=1)

        fig = px.line(df, markers=True, title="cpuloading")
        fig.update_layout(xaxis_title='points index', yaxis_title=u'cpuloading/%', yaxis_range=[0,100])
        fig.show()
