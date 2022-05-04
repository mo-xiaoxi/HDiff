#!/bin/bash
SHELL_FOLDER=$(cd "$(dirname "$0")";pwd)
find $SHELL_FOLDER/data/fuzz_data -name \*.json|xargs rm -rf
find $SHELL_FOLDER/data/log/ -name \*.log|xargs rm -rf
