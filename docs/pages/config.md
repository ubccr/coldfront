# Configuration

ColdFront can be configured via environment variables, an environment file, or
a python file which can be used for more advanced configuration settings. This
document covers the configuration settings available in ColdFront and the core
plugins. For information on installing ColdFront [see here](install.md).

## Configuration files

You can set environment varialbes via a file and ColdFront by default will look
for the following files:

- `.env` in the ColdFront project root
- `/etc/coldfront/coldfront.env`

You can also specify the path to an environment file using the `COLDFRONT_ENV`
environment variable. For example

```
COLDFRONT_ENV=/opt/coldfront/coldfront.env
```

For more advanced configurations, you can create a python file to override
ColdFront settings:

- `local_settings.py` relative to coldfront.config package
- `/etc/coldfront/local_settings.py`
- `local_settings.py` in the ColdFront project root

You can also specify the path to `local_settings.py` using the
`COLDFRONT_CONFIG` environment variable. For example:

```
COLDFRONT_CONFIG=/opt/coldfront/mysettings.py
```

## Simple Example

Here's a very simple example demonstrating how to configure ColdFront using
environment variables:

```
$ tee coldfront.env <<EOF
DEBUG=True
CENTER_NAME='University HPC'
PROJECT_ENABLE_PROJECT_REVIEW=False
DB_URL='mysql://user:password@127.0.0.1:3306/database'
EOF

$ COLDFRONT_ENV=coldfront.env coldfront runserver
```

## Configuration Variables

### Base settings

The following settings allow overriding basic ColdFront Django settings. For
more advanced configuration use `local_settings.py`.

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| ALLOWED_HOSTS        | A list of strings representing the host/domain names that ColdFront can server. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts) |
| DEBUG                | Turn on/off debug mode. Never deploy a site into production with DEBUG turned on. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#debug) |
| SECRET_KEY           | This is used to provide cryptographic signing, and should be set to a unique, unpredictable value. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#secret-key). If you don't provide this one will be generated each time ColdFront starts. |
| LANGUAGE_CODE        | A string representing the language code. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#language-code1)
| TIME_ZONE            | A string representing the time zone for this installation. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-TIME_ZONE) |

### ColdFront core settings

The following settings are ColdFront specific settings related to the core application.

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| CENTER_NAME          | The display name of your center      |
| CENTER_HELP_URL      | The URL of your help ticketing system |
| CENTER_PROJECT_RENEWAL_HELP_URL  | The URL of the article describing project renewals |
| CENTER_BASE_URL      | The base URL of your center. |
| PROJECT_ENABLE_PROJECT_REVIEW    | Enable or disable project reviews. Default True|
| ALLOCATION_ENABLE_ALLOCATION_RENEWAL    | Enable or disable allocation renewals. Default True |
| ALLOCATION_DEFAULT_ALLOCATION_LENGTH    | Default number of days an allocation is active for. Default 365 |
| ALLOCATION_ACCOUNT_ENABLED    | Allow user to select account name for allocation. Default True |
| INVOICE_ENABLED    | Enable or disable invoices. Default True |
| ONDEMAND_URL    | The URL to your Open OnDemand installation |
| LOGIN_FAIL_MESSAGE    | Custom message when user fails to login. Here you can paint a custom link to your user account portal |
| ENABLE_SU    | Enable administrators to login as other users. Default True |


### Database settings

The following settings configure the databse server to use: 

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| DB_URL               | The database connection url string   |

Examples:

```
DB_URL=mysql://user:password@127.0.0.1:3306/database
DB_URL=psql://user:password@127.0.0.1:8458/database
DB_URL=sqlite:////usr/share/coldfront/coldfront.db
```

### Email settings

The following settings configure emails in ColdFront. By default email is
disabled:

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| EMAIL_ENABLED        | Enable/disable email. Default False  |
| EMAIL_HOST           | Hostname of smtp server |
| EMAIL_PORT           | smtp port
| EMAIL_HOST_USER      | Username for smtp |
| EMAIL_HOST_PASSWORD  | password for smtp |
| EMAIL_USE_TLS        | Enable/disable tls. Default False  |
| EMAIL_SENDER        | Default sender email address |
| EMAIL_SUBJECT_PREFIX | Prefix to add to subject line |
| EMAIL_ADMIN_LIST        | List of admin email addresses. |
| EMAIL_TICKET_SYSTEM_ADDRESS        | Email address of ticketing system |
| EMAIL_DIRECTOR_EMAIL_ADDRESS        | Email address for director | 
| EMAIL_PROJECT_REVIEW_CONTACT        | Email address of review contact |
| EMAIL_DEVELOPMENT_EMAIL_LIST        | List of emails to send when in debug mode |
| EMAIL_OPT_OUT_INSTRUCTION_URL        | URL of article regarding opt out |
| EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS        | List of days to send email notifications for expiring allocatioins. Default 7,14,30 |
| EMAIL_SIGNATURE        | Email signature to add to outgoing emails |

### Plugin settings

#### LDAP Auth

!!! warning "Required"
    LDAP authentication backend requires `ldap3` and `django_auth_ldap`. 
    ```
    $ pip install ldap3 django_auth_ldap
    ```

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_AUTH_LDAP     | Enable LDAP Authentication Backend. Default False |
| AUTH_LDAP_SERVER_URI | URI of LDAP server |
| AUTH_LDAP_START_TLS | Enable/disable start tls. Default True  |
| AUTH_LDAP_USER_SEARCH_BASE | User search base dn |
| AUTH_LDAP_GROUP_SEARCH_BASE | Group search base dn |
| AUTH_LDAP_MIRROR_GROUPS | Enable/disable mirroring of groups. Default True  |

#### OpenID Connect Auth

!!! warning "Required"
    OpenID Connect authentication backend requires `mozilla_django_oidc`.
    ```
    $ pip install mozilla_django_oidc
    ```

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_AUTH_OIDC     | Enable OpenID Connect Authentication Backend. Default False |
| OIDC_OP_JWKS_ENDPOINT | URL of JWKS endpoint |
| OIDC_RP_SIGN_ALGO | Signature algorithm |
| OIDC_RP_CLIENT_ID | Client ID |
| OIDC_RP_CLIENT_SECRET | Client secret |
| OIDC_OP_AUTHORIZATION_ENDPOINT | OAuth2 authorization endpoint |
| OIDC_OP_TOKEN_ENDPOINT | OAuth2 token endpoint |
| OIDC_OP_USER_ENDPOINT | OAuth2 userinfo endpoint |
| OIDC_VERIFY_SSL | Verify ssl Deafult True |
| OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS | Token lifetime in seconds. Default 3600 |

#### Mokey

!!! warning "Required"
    Mokey depends on the OpenID Connect plugin above. You must also enable the
    OpenID Connect plugin via `PLUGIN_AUTH_OIDC=True`.

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_MOKEY         | Enable Mokey/Hydra OpenID Connect Authentication Backend. Default False|

#### Slurm

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_SLURM     | Enable Slurm integration. Default False |
| SLURM_SACCTMGR_PATH | Path to sacctmgr command. Default `/usr/bin/sacctmgr` |
| SLURM_NOOP | Enable/disable noop. Default False  |
| SLURM_IGNORE_USERS | List of user accounts to ignore when generating Slurm associations |
| SLURM_IGNORE_ACCOUNTS | List of Slurm accounts to ignore when generating Slurm associations |

#### XDMoD

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_XDMOD     | Enable XDMoD integration. Default False |
| XDMOD_API_URL | URL to XDMoD API |

#### FreeIPA

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_FREEIPA     | Enable FreeIPA integration. Default False |
| FREEIPA_KTNAME | Path to keytab file |
| FREEIPA_SERVER | Hostname of FreeIPA server |
| FREEIPA_USER_SEARCH_BASE | User search base dn |
| FREEIPA_ENABLE_SIGNALS | Enable/Disable signals. Default False |

#### iquota

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_IQUOTA     | Enable iquota integration. Default False |
| IQUOTA_KEYTAB | Path to keytab file |
| IQUOTA_CA_CERT | Path to ca cert |
| IQUOTA_API_HOST | Hostname of iquota server |
| IQUOTA_API_PORT | Port of iquota server |

## Advanced Configuration

ColdFront uses the [Django
settings](https://docs.djangoproject.com/en/3.1/topics/settings/). In most
cases, you can set custom configurations via environment variables above. If
you need more control over the configuration you can use a `local_settings.py`
file and override any Django settings. For example, instead of setting the
`DB_URL` environment variable above, we can create
`/etc/coldfront/local_settings.py` or create a `local_settings.py` file
in the coldfront project root and add our custom database configs as follows:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'coldfront',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    },
}
```
