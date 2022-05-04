#!/bin/sh
SHELL_FOLDER=$(cd "$(dirname "$0")";pwd)
cd $SHELL_FOLDER/docker/proxy
docker-compose down
docker-compose up -d

cd $SHELL_FOLDER/docker/server
docker-compose down
docker-compose up -d


docker exec proxy_varnish_1 varnishncsa -D -a -w /var/log/varnish/varnishncsa.log -F '"%{Host}i" %s \"%r\"'
