#!/usr/bin/env bash

set +x

# start ats
DISTRIB_ID=gentoo /opt/ats/bin/trafficserver start

if [ ! $@ ]; then
    tail -f /dev/null
else
    exec $@
fi