#!/bin/bash
SHELL_FOLDER=$(cd "$(dirname "$0")";pwd)
cd $SHELL_FOLDER/docker/proxy
docker-compose down

cd $SHELL_FOLDER/docker/server
docker-compose down
