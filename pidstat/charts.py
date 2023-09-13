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

def cleanup_file(args):
    global f0name
    header_first = False
    f = open(args.input)
    f0name = args.input + ".out"
    f0 = open(f0name, "w")
    print("open", f0name)
    for line in f:
        if re.match(r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9].*', line):
            if not re.match(r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9].+UID.+Command', line):
                f0.write(line)
            elif not header_first:
                header_first = True
                f0.write(line)
    f0.close()

# pidstat -t 1
def parse_thread(args):
    with open(f0name) as f:
        # First line is a table header
        header = f.readline().split()
        # But the first column has time instead of the word 'Time'
        header[0] = 'Time'
        df = pd.read_csv(f,names=header,delim_whitespace=True, usecols=[0,1,2,3,4,5,6,7,8,9,10])

    df['Command'] = df['Command'].str.replace("|__", "")
    df['key'] = df['TID'] + '-' + df['Command']

    # Add new datframe for the whole process stats
    dfsum = df[df.TID == '-']
    # Skip main summarized info for a process
    df = df[df.TID != '-']


    df["Time"] = pd.to_datetime(df["Time"])
    x = df["Time"].values.tolist()
    y = df["%CPU"].values.tolist()
    df = df.sort_values(by="Time")
    fig = px.line(df, x='Time', y='%CPU', color='key', markers=True, title=f0name)
    #fig.show()
    fig = px.line(dfsum, x='Time', y='%CPU', color='key', title='sum - ' + f0name)
    #fig.show()

    keys = set(dfsum['key'])
    dfcpu = pd.DataFrame(columns=['key', 'cpu'])

    for key in keys:
        dftmp = dfsum[dfsum['key'] == key]
        dfcpu.loc[len(dfcpu)]=[key, dftmp['%CPU'].mean()]

    dfcpu = dfcpu.sort_values(by='cpu', ascending=False)
    print(dfcpu.head(10))

    keys = set(df['key'])
    dftcpu = pd.DataFrame(columns=['key', 'cpu'])

    for key in keys:
        dftmp = df[df['key'] == key]
        dftcpu.loc[len(dftcpu)]=[key, dftmp['%CPU'].mean()]

    dftcpu = dftcpu.sort_values(by='cpu', ascending=False)
    print(dftcpu.head(30))


# pidtat 1
def parse_process(args):
    with open(f0name) as f:
        # First line is a table header
        header = f.readline().split()
        # But the first column has time instead of the word 'Time'
        header[0] = 'Time'
        df = pd.read_csv(f,names=header,delim_whitespace=True, usecols=[0,1,2,3,4,5,6,7,8,9])

    df['Command'] = df['Command'].str.replace("|__", "")
    df['key'] = df['PID'].astype('string') + '-' + df['Command']

    df["Time"] = pd.to_datetime(df["Time"])
    x = df["Time"].values.tolist()
    y = df["%CPU"].values.tolist()
    #df.plot.line()
 #   df = df.sort_values(by="Time")
    fig = px.line(df, x='Time', y='%CPU', color='key', markers=True)
    fig.show()
    fig = px.line(dfsum, x='Time', y='%CPU', color='key')
  #  fig.show()


def main():
    parser = argparse.ArgumentParser(description="Plot pidstat results")
    parser.add_argument('--input','-i',type=str,help="Input file")
    args = parser.parse_args()
    cleanup_file(args)
    #parse_process(args)
    parse_thread(args)

pd.options.display.max_rows = None
main()

