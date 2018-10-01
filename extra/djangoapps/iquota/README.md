# iquota reporting for Coldfront

Coldfront django extra app providing iquota reporting for Coldfront.
[iquota](https://github.com/ubccr/iquota) is a command line tool and associated
server application for reporting quotas from Isilon nfs mounts using the OneFS
API. User and group quotas are displayed on the Coldfront portal home page.

## Design

This app uses the iquota API to report user and group quotas. Kerberos is used
to authenticate to the API and a valid keytab file is required.

## Requirements

- pip install kerberos humanize requests

## Usage

To enable this extra app add or uncomment the following in your
local\_settings.py file:

```
    EXTRA_APPS += [
        'extra.djangoapps.iquota'
    ]

    IQUOTA_KEYTAB = '/path/to/user.keytab'
    IQUOTA_CA_CERT = '/etc/ipa/ca.crt'
    IQUOTA_API_HOST = 'localhost'
    IQUOTA_API_PORT = '8080'
    IQUOTA_USER_PATH = '/ifs/user'
    IQUOTA_GROUP_PATH = '/ifs/projects'
```
