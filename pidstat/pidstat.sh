#!/bin/bash
PERIOD=5 # unit is sec
COUNT=
PERIOD_MS=`expr $PERIOD \* 1000`

endf ()
{
    echo "endf"
 #   kill -SIGKILL $pidstatPID
 #   sudo kill -SIGKILL $perfPID
}

sudo ls

echo $1

if [ ! $1 ]; then
    OPT0=" "
    OPT1=" -a "
    echo "record system-wide"
else
    OPT0="-p $1"
    OPT1="-p $1"
fi

echo $PERIOD, $COUNT, $PERIOD_MS, $TARGET_PID
pidstat -t $OPT0 $PERIOD $COUNT > pidstat.log &
pidstatPID=$!
sudo perf stat -dd $OPT1 --per-thread --interval-print $PERIOD_MS 2> perf.log &
perfPID=$!
sar -w -u -I ALL $PERIOD > sar.log &


trap endf SIGINT

sleep 100000

