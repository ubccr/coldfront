# Deploying ColdFront in Production

This document outlines how to run ColdFront in production. ColdFront is written
in python3 and uses the Django web framework.  Here we showcase deploying
ColdFront using Gunicorn and nginx but any method for deploying Django in
production could be used. For a more comprehensive list of methods [see
here](https://docs.djangoproject.com/en/3.1/howto/deployment/).

## Preliminaries

It's recommended to create a non-root user for running ColdFront. The Gunicorn
worker processes will run under this user account. Also, create a directory for
installing ColdFront and related files.

```
$ useradd --system -m coldfront
$ mkdir /srv/coldfront
$ chown coldfront.coldfront /srv/coldfront
$ mkdir /etc/coldfront
```

!!! note
    This guide uses nginx. So be sure you have nginx installed:
    ```
    # yum/apt install nginx
    ```

## Install ColdFront

ColdFront can be installed from PyPI using any of the following methods.
ColdFront has a few optional dependencies that are used for enabling specific
features:


| extra         | Description            |
| :-------------|:-----------------------|
| ldap          |  ldap user search      |
| oidc          |  OIDC logins           |
| freeipa       |  freeipa plugin        |
| iquota        |  iquota plugin         |
| mysql         |  MySQL/MariaDB backend |
| pg            |  PostgreSQL backend    |



### Using uv (recommended)

```
$ uv tool install coldfront[ldap,freeipa,oidc]
```

### Using pip in a virtual environment

```
$ cd /srv/coldfront
$ python3 -mvenv venv
$ source venv/bin/activate
$ pip install --upgrade pip

# Adjust extras to suite your needs
$ pip install coldfront[ldap,freeipa,oidc,pg]
```

## Configure ColdFront

Create a config file for ColdFront. For a complete list of settings [see
here](config.md).

!!! note
    The config file needs to be readable by nginx user. Ensure you have the
    appropriate permissions set. For example:
    ```
    $ chmod 640 /etc/coldfront/coldfront.env
    $ chgrp nginx /etc/coldfront/coldfront.env
    ```

Create the file `/etc/coldfront/coldfront.env` and set at least the following
variables:

```bash

# Database connection
DB_URL=mysql://user:password@127.0.0.1:3306/database

# Path to store static assets
STATIC_ROOT=/srv/coldfront/static

# Name of your center
CENTER_NAME='University HPC'

# Cryptographic secret key
SECRET_KEY=
```

!!! danger "Danger"
    Never set `DEBUG` to True in production. You also MUST set `SECRET_KEY` in
    production or else each time ColdFront is started a new one will be
    generated. You can create a good secret key using the following command:
    ```
    $ python3 -c "import secrets; print(secrets.token_urlsafe())"
    ```

**Choosing a database backend:** ColdFront supports MariaDB/MySQL, PostgreSQL, or
SQLite. If you don't configure a database, it will use SQLite by default and will
place the database in the ColdFront working directory.  You may not want this for a production installation.

Install your preferred database and set the connection details using
the `DB_URL` variable as shown above.  

!!! note "Note: Install python database drivers"
    Be sure to install the extra package options when installing ColdFront for your chosen database. For example:
    ```
    # For mysql/mariadb
    $ pip install coldfront[mysql]
    # For postgresql
    $ pip install coldfront[pg]
    ```

## Initializing the ColdFront database

```
$ coldfront initial_setup
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ....
  ....
```

!!! warning "This should only be done once"
    You only need to initialize the ColdFront database once after you first
    install.


## Create the super user account

Run the command below to create a new super user account with a secure
password:

```
$ coldfront createsuperuser
```

!!! Tip  
    This command should prompt you to select a username, password, and email address for your super user account.  Set a secure password for use in production.  

## Deploy static files

This step allows serving all of ColdFront static assets (CSS/JavaScript/Images)
using nginx. For more information [see here](https://docs.djangoproject.com/en/3.1/howto/static-files/#deployment).
This command will deploy all static assets to the `STATIC_ROOT` path in the configuration step above.

```
$ coldfront collectstatic
```

## Create systemd unit file for ColdFront Gunicorn workers

Create file `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn instance to serve Coldfront
After=syslog.target network.target mariadb.service

[Service]
User=coldfront
Group=nginx
WorkingDirectory=/srv/coldfront
Environment="PATH=/srv/coldfront/venv/bin"
ExecStart=/srv/coldfront/venv/bin/gunicorn --workers 3 --bind unix:coldfront.sock -m 007 coldfront.config.wsgi

[Install]
WantedBy=multi-user.target
```

!!! note
    If using `uv tool` change the paths above accordingly.  Adjust the number
    of workers for your site specific needs using the `--workers` flag above.

## Start/enable ColdFront Gunicorn workers

```
$ systemctl start gunicorn.service
$ systemctl enable gunicorn.service

# Check for any errors
$ systemctl status gunicorn.service
```

## Create systemd unit file for ColdFront qcluster scheduled tasks
ColdFront uses Django Q to run scheduled tasks such as sending allocation expiration
warning emails. We need to create a unit file to run the qserver process or these
tasks will never run.

Create file `/etc/systemd/system/coldfrontq.service`:

```ini
[Unit]
Description=DjangoQ instance to run Coldfront scheduled tasks
After=syslog.target network.target mariadb.service gunicorn.service

[Service]
User=coldfront
Group=nginx
WorkingDirectory=/srv/coldfront
Environment="PATH=/srv/coldfront/venv/bin"
ExecStart=/srv/coldfront/venv/bin/coldfront qcluster

[Install]
WantedBy=multi-user.target
```

!!! note
    If using `uv tool` change the paths above accordingly.

## Start/enable ColdFront qcluster

```
$ systemctl start coldfrontq.service
$ systemctl enable coldfrontq.service

# Check for any errors
$ systemctl status coldfrontq.service
```
## Configure nginx

We now configure nginx to proxy requests to the ColdFront Gunicorn workers via
unix domain socket.

Create file `/etc/nginx/conf.d/coldfront.conf`:

```nginx
server {
    listen 443 ssl http2 default_server;

    # Note set these to the path of your SSL certs
    ssl_certificate /srv/coldfront/tls/coldfront.crt;
    ssl_certificate_key /srv/coldfront/tls/coldfront.key;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # modern configuration. tweak to your needs.
    ssl_protocols TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256';
    ssl_prefer_server_ciphers on;

    # HSTS (ngx_http_headers_module is required) (15768000 seconds = 6 months)
    add_header Strict-Transport-Security max-age=15768000;


    location /static/ {
        alias /srv/coldfront/static/;
    }

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/srv/coldfront/coldfront.sock;
    }
}
```

!!! tip "Use SSL in Production"
    Be sure to configure nginx with ssl when running in production. Creating
    and setting up SSL certificates is outside the scope of this document.


## Start/enable nginx

```
$ systemctl restart nginx.service
$ systemctl enable nginx.service
```
