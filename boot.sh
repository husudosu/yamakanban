#!/usr/bin/env bash

cd /root/
flask db upgrade

mkdir -p /root/data
mkdir -p /root/data/log

if [[ -z "${DEPLOY_ENV}" ]]; then
    DB_PORT=5432
else
    DB_PORT="${POSTGRES_PORT}"
fi

while ! nc -z "${POSTGRES_HOST}" "${DB_PORT}"; do sleep 1; done;

echo "Start supervisord"
exec supervisord -c /root/supervisord.conf
