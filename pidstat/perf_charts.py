#! /usr/bin/env python
#-*- coding: utf8 -*-

import re
import sys
import os
import pandas as pd
import argparse
import plotly.express as px
import plotly.graph_objects as go
import fileinput

f0name = ""
f0 = ""

f1name = ""
f1 = ""

header = ""

def comm_space_handle(line):
    ret = re.findall('^\s+\S+\s+([\s\S]+)\-\d+', line)
    if ret:
        str0 = ret[0]
        str1 = str0.replace(' ', '_')
        if str0 != str1:
            print("replaced in {} {} to {}".format(line, str0, str1))
        line = line.replace(str0, str1)
    return line

def cleanup_file(args):
    global f0name
    title_get = False
    f = open(args.input)
    f0name = args.input + ".out"
    f0 = open(f0name, "w")
    print("open", f0name)
    for line in f:
        if re.findall(r'not counted', line) or re.findall(r'not supported', line):
            pass
        else:
            if re.findall(r'counts unit events', line):
                if title_get:
                    continue
                title_get = True
            line = comm_space_handle(line)
            f0.write(line)
    f0.close()

def filter_file(args, event):
    global f1name
    f = open(f0name)
    f1name = args.input + ".rate.out"
    f1 = open(f1name, "w")
    print("open", f1name)
    for line in f:
        if re.findall(event, line):
            f1.write(line)
    f1.close()


def df_filter(df, event):
    df1 = df[df.events == event]
    if not df1.empty:
        return df1
    df1 = df[df.unit == event]
    return df1

pd.options.display.max_rows = None

def work(args):
    global header
    with open(f0name) as f:
        # First line is a table header
        header = f.readline().split()
        # But the first column has time instead of the word 'Time'
        del header[0]
        df = pd.read_csv(f,names=header,delim_whitespace=True, usecols=[0,1,2,3,4])
        df['counts'] = df['counts'].astype("float")
   
        dfclk   = df_filter(df, 'task-clock')
        dfctx   = df_filter(df, 'context-switches')
        dfmig   = df_filter(df, 'cpu-migrations')
        dfpgf   = df_filter(df, 'page-faults')
        dfcyc   = df_filter(df, 'cycles')
        dfins   = df_filter(df, 'instructions')
        dfbr    = df_filter(df, 'branches')
        dfbrm   = df_filter(df, 'branch-misses')
        dfl1d   = df_filter(df, 'L1-dcache-loads')
        dfl1dm  = df_filter(df, 'L1-dcache-load-misses')
        dfllc   = df_filter(df, 'LLC-loads')
        dfllcm  = df_filter(df, 'LLC-load-misses')
        dfl1i   = df_filter(df, 'L1-icache-loads')
        dfl1im  = df_filter(df, 'L1-icache-load-misses')
        dfdtlb  = df_filter(df, 'dTLB-loads')
        dfdtlbm = df_filter(df, 'dTLB-load-misses')
        dfitlb  = df_filter(df, 'iTLB-loads')
        dfitlbm = df_filter(df, 'iTLB-load-misses')

        fig = px.line(dfllcm, x='time', y='counts', color='comm-pid', markers=True)
        fig.show()


def work_rate(args):
    header = ['time', 'comm-pid', 'counts', 'events', 'rate']
    print(header)
    with open(f1name) as f:
        df = pd.read_csv(f,names=header,delim_whitespace=True, usecols=[0,1,2,3,5])
    print(df)
    df['rate'] = df['rate'].str.replace('%', '')
    df['rate'] = df['rate'].astype('float')
    fig = px.line(df, x='time', y='rate', color='comm-pid', markers=True, title=f0name)
    fig.show()

def main():
    parser = argparse.ArgumentParser(description="Plot pidstat results")
    parser.add_argument('--input','-i',type=str,help="Input file")
    args = parser.parse_args()
    cleanup_file(args)
    filter_file(args, 'LLC-load-misses')
    work_rate(args)

main()

