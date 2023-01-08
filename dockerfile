FROM python:3.10-bullseye
LABEL maintainer="Ferenc Nánási <husudosu94@gmail.com>"


ENV FLASK_APP=run.py \
    FLASK_ENV=production \
    TZ="Europe/Budapest"

RUN apt update && \
    apt upgrade -y && \
    apt install \
    libpq-dev \
    python3-dev \
    nginx \
    netcat \
    supervisor -y
RUN openssl req -x509 -nodes -days 365 -subj "/C=CA/ST=QC/O=Company, Inc./CN=yamakanban.local" -addext "subjectAltName=DNS:yamakanban.local" -newkey rsa:2048 -keyout /etc/ssl/private/nginx-selfsigned.key -out /etc/ssl/certs/nginx-selfsigned.crt;

# Install node.js and npm too.
# Donwload and install Node.js (https://github.com/nodejs/docker-node/blob/9220863a62a5f9d76bb761d1e385674de39224a6/19/bullseye/Dockerfile)
RUN curl -fsSLO --compressed https://nodejs.org/dist/v16.9.1/node-v16.9.1-linux-x64.tar.gz &&  \
tar -xf node-v16.9.1-linux-x64.tar.gz -C /usr/local --strip-components=1 --no-same-owner && \
ln -s /usr/local/bin/node /usr/local/bin/nodejs && \
node --version && \
npm --version

WORKDIR /root
COPY REQUIREMENTS.txt ./
RUN pip install -r REQUIREMENTS.txt

COPY run.py \
    config.py \
    boot.sh \ 
    configs/supervisord.conf \ 
    configs/nginx/nginx.conf \
    ./

COPY api api
COPY migrations migrations
COPY frontend frontend

# Build frontend
WORKDIR /root/frontend
RUN npm install && npm run build && npm prune --production
WORKDIR /root

COPY ./configs/nginx/http /etc/nginx/sites-enabled/default
COPY ./configs/nginx/nginx.conf /etc/nginx/nginx.conf
RUN chmod 777 boot.sh

EXPOSE 80
EXPOSE 443
