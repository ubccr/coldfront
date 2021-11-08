# syntax=docker/dockerfile:experimental
FROM python:3.6

EXPOSE 9000
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
ARG NANITES_CLIENT_COMMIT=8eebbe1536fc21f8c7baf362194a8dd90b4f0663
ARG IFXMAIL_CLIENT_COMMIT=cc1a9f9cc6cdb951828b6b912bc830c0172785f1
ARG IFXUSER_COMMIT=eecc611fa78f0c2ebf5f476ecff2cd5cabe80467
ARG FIINE_CLIENT_COMMIT=e79f569aa22b43876945bfb75cf169b11a555138
ARG IFXVALIDCODE_COMMIT=4dd332c5a8e13d904a90da014094406a81b617e6
ARG IFXBILLING_COMMIT=5f9895d0fcfbd6c83db263b552158222f51f7023

RUN --mount=type=ssh pip install --upgrade pip && \
    pip install gunicorn && \
    pip install 'Django>2.2,<3' && \
    pip install django-author==1.0.2 && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxurls.git@${IFXURLS_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/nanites.client.git@${NANITES_CLIENT_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxmail.client.git@${IFXMAIL_CLIENT_COMMIT} && \
    pip install git+ssh://git@github.com/harvardinformatics/ifxuser.git@${IFXUSER_COMMIT} && \
    pip install git+ssh://git@gitlab-int.rc.fas.harvard.edu/informatics/fiine.client.git@${FIINE_CLIENT_COMMIT} && \
    pip install git+ssh://git@gitlab-int.rc.fas.harvard.edu/informatics/ifxvalidcode.git@${IFXVALIDCODE_COMMIT} && \
    pip install git+ssh://git@gitlab-int.rc.fas.harvard.edu/informatics/ifxbilling.git@${IFXBILLING_COMMIT} && \
    pip install ldap3 django_auth_ldap && \
    pip install -r requirements.txt

COPY . .

ENV PYTHONPATH /usr/src/app

CMD ./manage.py collectstatic --no-input && ./manage.py makemigrations && ./manage.py migrate && /usr/bin/supervisord -n

