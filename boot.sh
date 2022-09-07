#!/usr/bin/env bash

cd /root/
flask db upgrade

mkdir -p /root/data
mkdir -p /root/data/log

echo "Start supervisord"
exec supervisord -c /root/supervisord.conf
