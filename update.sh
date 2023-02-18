#!/usr/bin/env bash
docker-compose stop
git pull --recurse-submodules
docker-compose build
docker-compose up
