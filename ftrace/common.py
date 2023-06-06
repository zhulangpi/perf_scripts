#! /usr/bin/env python
#-*- coding: utf8 -*-

def ts2us(ts):
    return round(ts * 1000000, 3)

def pr_err(*a):
    # Here a is the array holding the objects
    # passed as the argument of the function
    print(*a, file=sys.stderr)

