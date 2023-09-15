#! /usr/bin/env python
#-*- coding: utf8 -*-

import sys
import os
import psutil

def ts2us(ts):
    return round(ts * 1000000, 3)

def pr_err(*a):
    # Here a is the array holding the objects
    # passed as the argument of the function
    print(*a, file=sys.stderr)

def showmem():
    print("current meminfo {}".format(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024 / 1024))

