#!/usr/bin/env bash

set +x

# start ats
/opt/ts/bin/trafficserver start

if [ ! $@ ]; then
    tail -f /dev/null
else
    exec $@
fi