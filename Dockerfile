# syntax=docker/dockerfile:experimental
FROM python:3.6

EXPOSE 80
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsasl2-dev libldap2-dev libssl-dev \
    nginx supervisor \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir ~/.ssh && echo "Host git*\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config
RUN echo 'TLS_REQCERT allow' >> /etc/ldap/ldap.conf

RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY etc/nginx.conf /etc/nginx/sites-available/default
COPY etc/supervisor.conf /etc/supervisor/conf.d/app.conf

WORKDIR /usr/src/app
COPY requirements.txt ./

ARG IFXURLS_COMMIT=549af42dbe83d07b12dd37055a5ec6368d4b649
ARG NANITES_CLIENT_COMMIT=e4099cb6c9edadf2f722e8c26c413caf7e2c1c51
ARG IFXUSER_COMMIT=bcc84807bde34f8277a4d2def0503151ab89d174
ARG FIINE_CLIENT_COMMIT=b944730dcdf7de9df3479efdeb48848813a14032
ARG IFXBILLING_COMMIT=1e8256e78c5b8bb83ef338b4ed95f95f5a9381cd

RUN --mount=type=ssh pip install --upgrade pip && \
    pip install gunicorn && \
    pip install 'Django>2.2,<3' && \
    pip install django-author==1.0.2 && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxurls.git@${IFXURLS_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/nanites.client.git@${NANITES_CLIENT_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxuser.git@${IFXUSER_COMMIT} && \
    pip install git+ssh://git@gitlab-int.rc.fas.harvard.edu/informatics/fiine.client.git@${FIINE_CLIENT_COMMIT} && \
    pip install git+ssh://git@gitlab-int.rc.fas.harvard.edu/informatics/ifxbilling.git@${IFXBILLING_COMMIT} && \
    pip install ldap3 django_auth_ldap && \
    pip install -r requirements.txt

COPY . .

ENV PYTHONPATH /usr/src/app

CMD ./manage.py collectstatic --no-input && ./manage.py makemigrations && ./manage.py migrate && /usr/bin/supervisord -n

