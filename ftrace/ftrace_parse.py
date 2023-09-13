#! /usr/bin/env python
#-*- coding: utf8 -*-

from interval import Interval
import re
from tasks import task, tasks
from events import event, eventlist
from sched import sched_switch_event, sched_waking_event
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import plotly.express as px
import pandas as pd
from common import ts2us

class ftrace():
    def __init__(self, logfile=None):
        self.tasklist = tasks()
        self.elist = eventlist()
        self.wakechain = {}
        if not logfile:
            logfile = "ftrace.log"
        with open(logfile) as f:
            for line in f:
                ret = re.findall("\s+(\S+)\-(\d+)\s+\((.*?)\)\s+\[(\d+)\]\s+\S+\s+(\S+)\:\s+(\S+)\:([\S+\s+]+)\n", line)
                #ret = re.findall("\s+(\S+)\-(\d+)\s+\((.*?)\)\s+\[(\d+)\]\s+(\S+)\:\s+(\S+)\:([\S+\s+]+)\n", line)
                if ret:
                    comm,pid,tgid,cpu,timestamp,eventtype,trace = ret[0]
                    timestamp = float(timestamp)
                    if tgid == "-------":
                        tgid = pid
                    pid = int(pid)
                    t = task(comm, pid, tgid)
                    if t not in self.tasklist:
                        self.tasklist.addtask(t)
                    e = event(t, cpu, timestamp, eventtype, trace)
                    self.elist.append(e)
                else:
                    print("parse failed:", line)
        self.elist.check_if_data_lost()

    # usage: ftrace.eventlist_slice(359.694424, 360.694424)
    def eventlist_slice(self, start, end, replace = 0):
        inter = Interval(start, end)
        if replace:
            self.elist = self.elist.slice(inter)
        else:
            return self.elist.slice(inter)

    def calc_sched_latency(self):
        waked_tsks = {} # key = tsk, val = waked_ts
        preempted_tsks = {} # key = tsk, val = preempted_ts
        sleep_tsks = {} # key = tsk, val = sleep duration
        for e in self.elist:
            if e.eventtype == "sched_switch":
                switch_in_pid = e.trace.next_pid
                switch_out_pid = e.trace.prev_pid
                switch_in_tsk = None
                if switch_in_pid in self.tasklist:
                    switch_in_tsk = self.tasklist[switch_in_pid]
                switch_out_tsk = self.tasklist[switch_out_pid]
                prev_stat = e.trace.prev_state
                ts = e.timestamp

                # 被唤醒后第一次执行，统计调度延迟
                if switch_in_tsk in waked_tsks:
                    #if ts2us(ts - waked_tsks[switch_in_tsk]) > 100:
                    #    print("sched latency of {} is {}, at {}-{}".format(switch_in_tsk, ts2us(ts - waked_tsks[switch_in_tsk]),  waked_tsks[switch_in_tsk], ts))
                    switch_in_tsk.add_sched_latency(waked_tsks[switch_in_tsk], ts2us(ts - waked_tsks[switch_in_tsk]))
                    if switch_in_tsk.sched_latency_in_period:
                        switch_in_tsk.add_sched_latency_in_period(ts2us(ts - waked_tsks[switch_in_tsk]))
                    del waked_tsks[switch_in_tsk]

                # 被抢占后第一次执行，统计被抢占时间
                if prev_stat == "R":
                    preempted_tsks[switch_out_tsk] = e.timestamp

                if switch_in_tsk in preempted_tsks:
                    #if ts2us(ts - preempted_tsks[switch_in_tsk]) > 100:
                    #    print("preempted latency of {} is {}, at {}-{}".format(switch_in_tsk, ts2us(ts - preempted_tsks[switch_in_tsk]),  preempted_tsks[switch_in_tsk], ts))
                    switch_in_tsk.add_sched_latency(preempted_tsks[switch_in_tsk], ts2us(ts - preempted_tsks[switch_in_tsk]))
                    if switch_in_tsk.sched_latency_in_period:
                        switch_in_tsk.add_sched_latency_in_period(ts2us(ts - preempted_tsks[switch_in_tsk]))
                    del preempted_tsks[switch_in_tsk]

                if prev_stat == "S":
                    sleep_tsks[switch_out_tsk] = e.timestamp
                    if switch_out_tsk.run_period:
                        switch_out_tsk.update_run_period(e.timestamp)

            if e.eventtype == "sched_waking":
                waked_pid = e.trace.pid
                waked_tsk = self.tasklist[waked_pid]
                waked_tsks[waked_tsk] = e.timestamp
                if waked_tsk in sleep_tsks:
                    waked_tsk.add_sleep_ts(sleep_tsks[waked_tsk], ts2us(e.timestamp - sleep_tsks[waked_tsk]))
                    waked_tsk.append_run_period_ts(e.timestamp)
                    waked_tsk.append_run_period(0)
                    waked_tsk.append_sched_latency_in_period(0)
                    del sleep_tsks[waked_tsk]

                waker_tsk = e.task
                waker_tsk = self.tasklist[e.task]
                self.stat_waking_events(waker_tsk, waked_tsk)

    # 统计线程sleep状态下，从一次wakeup到再次进入sleep的总时间、总调度延迟时间
    # 反应了一次运行周期下，线程的延迟

    def show_sched_latency_all(self, topN = 100000):
        i = 0
        sorted_tsk = sorted(self.tasklist.items(), key = lambda kv:kv[1].max_sched_latency(), reverse=True)
        print("{:<8} {:<16} {:>10} {:>16} {:>16}".format("pid", "comm", "avg_latency/us", "max_lat/us", "max_lat_switch_in_time/s"))
        for tsk in sorted_tsk:
            if i > topN:
                break
            tsk = tsk[1]
            if tsk.max_sched_latency():
                i = i + 1
                print("{:<8} {:<16} {:>10.3f} {:>16} {:>16.6f}".format(tsk.pid, tsk.name,
                        tsk.avg_sched_latency(), tsk.max_sched_latency(),
                        tsk.max_sched_latency_ts() + tsk.max_sched_latency()/1000000))
        '''

        for pid in self.tasklist:
            tsk = self.tasklist[pid]
            print("{:<8} {:<16} {:>10.3f} {:>16} {:>16}".format(tsk.pid, tsk.name, tsk.avg_sched_latency(), tsk.max_sched_latency(), self.max_sched_latency_ts()))

            '''
    def show_sched_latency_by_pid(self, pid):
        tsk = self.tasklist[pid]
        print("{:<8} {:<16} {:>10.3f} {:>10}".format(tsk.pid, tsk.name, tsk.avg_sched_latency(), tsk.max_sched_latency()))

    def plot_sched_latency_all(self):
        pids = []
        avg_sl = []
        max_sl = []
        for pid in self.tasklist:
            tsk = self.tasklist[pid]
            pids.append(pid)
            avg_sl.append(tsk.avg_sched_latency())
            max_sl.append(tsk.max_sched_latency())
        plt.plot(pids, avg_sl, 'rx')
        plt.plot(pids, max_sl, 'b.')
        plt.show()

    def plot_sched_latency_tgid(self, tgid):
        pids = []
        avg_sl = []
        max_sl = []
        for pid in self.tasklist:
            tsk = self.tasklist[pid]
            if tsk.tgid != tgid:
                continue
            pids.append(pid)
            avg_sl.append(tsk.avg_sched_latency())
            max_sl.append(tsk.max_sched_latency())
        plt.plot(pids, avg_sl, 'rx')
        plt.plot(pids, max_sl, 'b.')
        plt.show()

    def stat_waking_events(self, waker, waked):
        if waked not in self.tasklist or waker not in self.tasklist:
            return

        waker.add_waked(waked)
        waked.add_waker(waker)

        key = (waker, waked)
        if key not in self.wakechain:
            self.wakechain[key] = 0
        self.wakechain[key] = self.wakechain[key] + 1

    def stat_waked_by_pid(self, pid):
        tsk = self.tasklist[pid]
        print("show waked for {}".format(tsk))
        for k in tsk.wakeds:
            print(k, tsk.wakeds[k])

    def stat_waker_by_pid(self, pid):
        tsk = self.tasklist[pid]
        print("show waker for {}".format(tsk))
        for k in tsk.wakers:
            print(k, tsk.wakers[k])

    def nx_wakechain(self):
        self.wakechain = dict(sorted(self.wakechain.items(), key = lambda x:x[1], reverse = True))
        plt.figure(figsize=(80,80))
        G = nx.DiGraph()
        count = 0
        for key in self.wakechain:
            if count > 50:
                break
            else:
                count = count + 1
            print(key[0], key[1], self.wakechain[key])

            frompt = str(key[0].pid) + "-" + key[0].name
            topt = str(key[1].pid) + "-" + key[1].name
            weight = self.wakechain[key]
            G.add_weighted_edges_from([(frompt, topt, weight)])

        pos = nx.spring_layout(G, iterations=50)
        nx.draw(G, pos, with_labels=True, node_color = 'r', node_size=300)
        #nx.draw(G, with_labels=True, pos=nx.spring_layout(G, iterations=10), node_color = 'r', node_size=300, font_size = 10)
 #           width = [float(v['weight']) for (r, c, v) in G.edges(data = True)])
        edge_labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels = edge_labels)
        plt.show()

    def show_wakechain(self):
        self.wakechain = dict(sorted(self.wakechain.items(), key = lambda x:x[1], reverse = True))
        for key in self.wakechain:
            print("{} ==> {}: {:>8}".format(key[0], key[1], self.wakechain[key]))

    def show_sched_lantecy_by_tgid(self, tgid):
        for tsk in self.tasklist:
            task = self.tasklist[tsk]
            if task.tgid == tgid:
                print("{:<16} {:<8}".format(task.name, tsk), end='')
                task.show_sched_latency_each_period()

    # usage: calc_runtime_timerange(1, [0], [200,300])
    # this will calc task 1 running time on cpu0 between 200s-300s
    # currlist 代表cpu上当前运行着的任务的pid
    def calc_runtime_timerange(self, pid, cpulist, time_range, currlist = []):
        elist = self.eventlist_slice(time_range[0], time_range[1])
        runtime = [-1] * len(cpulist)
        switchin_time = [0] * len(cpulist)
        sumtime = 0
        if currlist:
            tmplist = currlist
        else:
            tmplist = [0] * len(cpulist)
        for e in elist:
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


    # usage: calc_cpu_loading([0,1,2], 0.1, [200,300])
    # this will calc cpu loading of cpu 0,1,2 between time of [200, 300]s, interval of time is 0.1s
    def calc_cpu_loading(self, cpulist, time_interval, time_range = []):
        if not cpulist:
            print("empty cpulist")
            return
        if time_interval < 0.1:
            print("too small interval will meaningless")

        elist = self.elist
        if time_range:
            if time_range[0] < elist.start():
                time_range[0] = elist.start()
            if time_range[1] > elist.end():
                time_range[1] = elist.end()
        else:
            time_range = [elist.start(), elist.end()]
        elist = self.eventlist_slice(time_range[0], time_range[1])
        print(time_range)

        ts = []
        loadings = [ [] for x in  range(len(cpulist) + 1) ]
        currlist = []
        print(loadings, cpulist, len(cpulist))
        for t in np.arange(time_range[0], time_range[1], time_interval):
            if t + time_interval > time_range[1]:
                break
            ts.append(t)
            total_loading = 0

            for idx, c in enumerate(cpulist):
                print("in  {}".format(currlist))
                sumtime, currlist = self.calc_runtime_timerange(0, [c], [t, t + time_interval], currlist)
                print("out {}".format(currlist))
                loading = 100 * sumtime / time_interval
                loadings[idx].append(loading)
                total_loading = total_loading + loading
            loadings[-1].append(total_loading)

        loadings[-1] = [ x / len(cpulist) for x in loadings[-1]]
        print(ts)
        print(loadings[-1])
        keys = cpulist
        keys.append("sum")
        df = pd.DataFrame(dict(zip(keys, loadings)))
        fig = px.line(df, markers=True, title="cpuloading")
        fig.show()
 #       for idx, l in enumerate(loadings):
  #          plt.plot(ts,  loadings[idx])
      #      px.line()
   #         plt.show()

        #plt.plot(ts,  loadings[-1])
