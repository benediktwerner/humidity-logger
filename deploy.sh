#!/bin/sh

set -e

[ $# -eq 0 ] && echo "Pass hostname to deploy to as argument" && exit 1

host="wernerfamily@$1"

ssh host 'mkdir -p ~/humidity-logger'
scp logger.py $host:~/humidity-logger/
scp humidity-logger.service $host:humidity-logger/
ssh $host 'sudo cp ~/humidity-logger/humidity-logger.service /etc/systemd/system/'
