#!/bin/sh

scp logger.py humidity1:humidity-logger/
scp humidity-logger.service humidity1:humidity-logger/
ssh humidity1 'sudo cp ~/humidity-logger/humidity-logger.service /etc/systemd/system/'
