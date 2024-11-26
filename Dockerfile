# syntax=docker/dockerfile:experimental

# to build for a development environment, run the following command:
# docker build --build-arg build_env=dev -t coldfront --ssh default . --network=host
FROM python:3.10

ARG build_env=production
ENV BUILD_ENV=$build_env

LABEL org.opencontainers.image.source=https://github.com/fasrc/coldfront
LABEL org.opencontainers.image.description="fasrc coldfront application"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && apt-get install -y redis redis-server \
    && apt-get install -y libsasl2-dev libldap2-dev libssl-dev \
    && apt-get install -y sssd sssd-tools supervisor \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir ~/.ssh && echo "Host git*\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config

WORKDIR /usr/src/app
COPY requirements.txt ./

ARG IPYTHON_STARTUP=/root/.ipython/profile_default/startup
RUN mkdir -p ${IPYTHON_STARTUP}
COPY etc/ipython_init.py ${IPYTHON_STARTUP}


RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

RUN if [ "${BUILD_ENV}" = "dev" ]; then pip install django-redis django-debug-toolbar; fi

RUN pip install django-prometheus gunicorn

ENV PYTHONPATH /usr/src/app:/usr/src/app/ifxreport:/usr/src/app/ifxbilling:/usr/src/app/fiine.client:/usr/src/app/ifxurls:/usr/src/app/nanites.client:/usr/src/app/ifxuser:/usr/src/app/ifxmail.client:/usr/src/app/ifxec

RUN mkdir -p /usr/src/app/media/reports

RUN printf "deb http://ftp.us.debian.org/debian buster main" > /etc/apt/sources.list.d/backports.list && \
    apt-get update && apt-get install libreadline7 && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 80
EXPOSE 25

CMD ["/bin/bash", "./container_startup.sh"]
