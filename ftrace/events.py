#! /usr/bin/env python
#-*- coding: utf8 -*-

from interval import Interval
from bisect import bisect_left, bisect
import re
from tasks import task, tasks
from sched import sched_switch_event, sched_waking_event


class event:
    __slots__ = ('task', 'cpu', 'timestamp', 'eventtype', 'trace')

    def __init__(self, tsk, cpu, timestamp, eventtype, trace):
        self.task = tsk
        self.cpu = int(cpu, 10)
        self.timestamp = timestamp
        self.eventtype = eventtype
        if self.eventtype == "sched_switch":
            self.trace = sched_switch_event(trace)
        if self.eventtype == "sched_waking":
            self.trace = sched_waking_event(trace)


    def __repr__(self):
        return "Event(type={} task={}, cpu={}, timestamp={:.06f}, trace={}".format(
        self.eventtype, self.task, self.cpu, self.timestamp, self.trace,)


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

