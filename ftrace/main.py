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
from ftrace_parse import ftrace
import sys, getopt

inputfile = "ftrace.log"

try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:o:", ["ifile=","ofile="])
except getopt.GetoptError:
    print("main.py -i <inputfile> -o <outputfile>")
    sys.exit(2)
for opt, arg in opts:
   if opt == '-h':
       print("main.py -i <inputfile> -o <outputfile>")
       sys.exit()
   elif opt in ("-i", "--ifile"):
       inputfile = arg
   elif opt in ("-o", "--ofile"):
       outputfile = arg

print("inputfile:", inputfile)
ft = ftrace(inputfile)
#ft.tasklist.showall()

#ft.eventlist_slice(359.694424, 360.694424)

ft.elist.check_if_data_lost()

ft.calc_sched_latency()

ft.show_sched_latency_all()

#ft.plot_sched_latency_all()
#ft.plot_sched_latency_tgid(6873)

#ft.nx_wakechain()
#ft.show_wakechain()


#ft.tasklist[8138].slot_wake()
#ft.stat_waker_by_pid(8138)
#ft.stat_waked_by_pid(8138)

#'''

for tsk in ft.tasklist:
    task = ft.tasklist[tsk]
#    if 0 or task.tgid == 6713:
    if tsk == 18586:
        ft.tasklist[tsk].show_sched_latency()
      #  ft.tasklist[tsk].plot_sched_latency()
     #   ft.tasklist[tsk].show_sleep_ts()
    #    ft.tasklist[tsk].plot_sleep_ts()
 #       print("{:<16} {:<8}".format(task.name, tsk), end='')
 #       task.show_sched_latency_each_period()
 #       ft.tasklist[tsk].plot_sched_latency_each_period()

#'''
#ft.show_sched_lantecy_by_tgid(3239)


