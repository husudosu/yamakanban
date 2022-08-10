#!/usr/bin/env bash

cd /root/
flask db upgrade

mkdir -p /root/data
mkdir -p /root/data/log

exec supervisord -c /root/supervisord.conf
