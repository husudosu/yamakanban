FROM python:3.10-bullseye
LABEL maintainer="Ferenc Nánási <husudosu94@gmail.com>"

ENV FLASK_APP=wsgi.py \
    FLASK_ENV=production \
    TZ="Europe/Budapest"

RUN apt update && apt install \
    libpq-dev \
    python3-dev \
    nginx \
    build-essential \
    supervisor \
    cron \
    -y && \
    python3 -m pip install --upgrade pip

# Install python requirements
COPY --chown=crm:crm REQUIREMENTS.txt ./
RUN pip install -r REQUIREMENTS.txt
