#!/usr/bin/env bash
cd frontend && npm ci --production && npm run build && cd .. && docker-compose -f docker-compose.yml build