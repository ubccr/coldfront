# iquota reporting for ColdFront

ColdFront plugin providing iquota reporting for ColdFront.
[iquota](https://github.com/ubccr/iquota) is a command line tool and associated
server application for reporting quotas from CCR storage nfs mounts. Storage
quotas are displayed on the ColdFront portal home page.

## Design

This app uses the iquota API to report quotas. Kerberos is used
to authenticate to the API and a valid keytab file is required.

## Requirements

- uv sync --extra iquota

## Usage

To enable this plugin set the following environment variables:

```
PLUGIN_IQUOTA=True
IQUOTA_KEYTAB='/path/to/user.keytab'
IQUOTA_CA_CERT='/etc/ipa/ca.crt'
IQUOTA_API_HOST='localhost'
IQUOTA_API_PORT='8080'
```
