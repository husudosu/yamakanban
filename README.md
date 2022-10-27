# My JWT auth flask boilerplate

A simple JWT handler with role management for my Flask REST backends + Mobile app frontends.

Lot inspiration came from [Flask-Security-Too](https://github.com/Flask-Middleware/flask-security/) library.

## Features

This boilerplate using Flask-JWT-Extended, so you can use any decorators which included on library.

-   User, Role handling,
-   Custom decorators for requiring roles and accept_roles,
-   Handling of users "forgot password"

## The project almost ready for production use, only few things missing:

-   Full test coverage, write "forgot password" tests missing,
-   Create a docker contarized version

## How to use (Docker)

```bash
cp sample.env .env.production
# Edit your settings
nano .env.production
docker-compose up -d
```

## How to use (Without docker)

Run with gunicorn:

```bash
cp sample.env .env.production
# Edit your settings
nano .env.production
# Run gunicorn
export FLASK_APP=run.py
export FLASK_ENV=production
gunicorn -b 0.0.0.0:5000 -w 4 run:app
```

It's recommended to use NGINX or Apache for production use!
Check out [Deploying Gunicorn](https://docs.gunicorn.org/en/stable/deploy.html)

## Development use

```bash
cp sample.env .env.development
# Edit your settings
nano .env.development
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run -h 0.0.0.0 -p 5000
```

## Testing

```bash
# On your virtualenv
pip install pytest coverage
# Running tests
coverage run -m pytest
# For coverage report run:
coverage report -m
```

## Optimized gunicorn launch

gunicorn --worker-class=gevent --worker-connections=1000 --workers=3 run:app

## Use this Socket.IO deploy

gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 run:app

## Create self-signed key

openssl req -x509 -nodes -days 365 -subj "/C=CA/ST=QC/O=Company, Inc./CN=trelloclone.local" -addext "subjectAltName=DNS:trelloclone.local" -newkey rsa:2048 -keyout nginx-selfsigned.key -out nginx-selfsigned.crt;
