#! /usr/bin/env python
#-*- coding: utf8 -*-

from interval import Interval
import re
from tasks import task, tasks
from events import event, eventlist
from sched import sched_switch_event, sched_waking_event
import matplotlib.pyplot as plt
import networkx as nx
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

    def eventlist_slice(self, start, end):
        inter = Interval(start, end)
        self.elist = self.elist.slice(inter)

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

    def show_sched_latency_all(self):
        for pid in self.tasklist:
            tsk = self.tasklist[pid]
            print("{:<8} {:<16} {:>10.3f} {:>10}".format(tsk.pid, tsk.name, tsk.avg_sched_latency(), tsk.max_sched_latency()))

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



