# syntax=docker/dockerfile:experimental

# to build for a development environment, run the following command:
# docker build --build-arg build_env=dev -t coldfront --ssh default . --network=host

FROM python:3.8

ARG build_env=production
ENV BUILD_ENV=$build_env

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

ARG IFXURLS_COMMIT=549af42dbe83d07b12dd37055a5ec6368d4b649
ARG NANITES_CLIENT_COMMIT=1e67ce787e27c9c0e32a4c97a4967c297d30b7cf
ARG IFXUSER_COMMIT=039a7a62cd67255bcb8992daec3b71bd433581b2
ARG IFXMAIL_CLIENT_COMMIT=8f728ff54441d2f2449fd3c31b75f0f77372b5f2
ARG FIINE_CLIENT_COMMIT=112858d4115ee6447ab9e396403fc5b48858cb70
ARG IFXEC_COMMIT=0c09c90890fb87d4db22c635a6c403c89e1a957f
ARG IFXBILLING_COMMIT=812a13788f04e2716c7337fa66baa9e26105c387

RUN --mount=type=ssh pip install --upgrade pip && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxurls.git@${IFXURLS_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/nanites.client.git@${NANITES_CLIENT_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxuser.git@${IFXUSER_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxmail.client.git@${IFXMAIL_CLIENT_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/fiine.client.git@${FIINE_CLIENT_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxec.git@${IFXEC_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxbilling.git@${IFXBILLING_COMMIT} && \
    pip install -r requirements.txt

COPY . .

RUN if [ "${BUILD_ENV}" = "dev" ]; then pip install django-redis reportlab==3.6.6 django-debug-toolbar; fi

RUN pip install ldap3 django_auth_ldap django-author==1.0.2 django-prometheus gunicorn

ENV PYTHONPATH /usr/src/app:/usr/src/app/ifxreport

RUN mkdir -p /usr/src/app/media/reports

RUN printf "deb http://ftp.us.debian.org/debian buster main" > /etc/apt/sources.list.d/backports.list && \
    apt-get update && apt-get install libreadline7 && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 80
EXPOSE 25

CMD ["/bin/bash", "./container_startup.sh"]
