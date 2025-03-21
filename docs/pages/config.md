# Configuration

ColdFront can be configured via environment variables, an environment file, or
a python file which can be used for more advanced configuration settings. This
document covers the configuration settings available in ColdFront and the core
plugins. For information on installing ColdFront [see here](install.md).

## Configuration files

You can set environment variables via a file and ColdFront by default will look
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

| Name                       | Description                          |
| :------------------------- |:-------------------------------------|
| ALLOWED_HOSTS              | A list of strings representing the host/domain names that ColdFront can serve. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts) |
| DEBUG                      | Turn on/off debug mode. Never deploy a site into production with DEBUG turned on. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#debug) |
| SECRET_KEY                 | This is used to provide cryptographic signing, and should be set to a unique, unpredictable value. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#secret-key). If you don't provide this one will be generated each time ColdFront starts. |
| LANGUAGE_CODE              | A string representing the language code. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#language-code)
| TIME_ZONE                  | A string representing the time zone for this installation. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-TIME_ZONE) |
| Q_CLUSTER_RETRY            | The number of seconds Django Q broker will wait for a cluster to finish a task. [See here](https://django-q.readthedocs.io/en/latest/configure.html#retry) |
| Q_CLUSTER_TIMEOUT          | The number of seconds a Django Q worker is allowed to spend on a task before it’s terminated. IMPORTANT NOTE: Q_CLUSTER_TIMEOUT must be less than Q_CLUSTER_RETRY. [See here](https://django-q.readthedocs.io/en/latest/configure.html#timeout) |
| SESSION_INACTIVITY_TIMEOUT | Seconds of inactivity after which sessions will expire (default 1hr). This value sets the `SESSION_COOKIE_AGE` and the session is saved on every request. [See here](https://docs.djangoproject.com/en/4.1/topics/http/sessions/#when-sessions-are-saved) |

### Template settings

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| STATIC_ROOT          | Path to the directory where collectstatic will collect static files for deployment. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-STATIC_ROOT) |
| SITE_TEMPLATES     | Path to a directory of custom templates. Add custom templates here. This path will be added to TEMPLATES DIRS. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-TEMPLATES-DIRS) |
| SITE_STATIC          | Path to a directory of custom static files. Add custom css here. This path will be added to STATICFILES_DIRS [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-STATICFILES_DIRS) |

### ColdFront core settings

The following settings are ColdFront specific settings related to the core application.

| Name                                   | Description                                    |
| :--------------------------------------|:-----------------------------------------------|
| CENTER_NAME                            | The display name of your center                |
| CENTER_HELP_URL                        | The URL of your help ticketing system          |
| CENTER_PROJECT_RENEWAL_HELP_URL        | The URL of the article describing project renewals |
| CENTER_BASE_URL                        | The base URL of your center.                   |
| PROJECT_ENABLE_PROJECT_REVIEW          | Enable or disable project reviews. Default True|
| ALLOCATION_ENABLE_ALLOCATION_RENEWAL   | Enable or disable allocation renewals. Default True |
| ALLOCATION_DEFAULT_ALLOCATION_LENGTH   | Default number of days an allocation is active for. Default 365 |
| ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT | Enable or disable allocation change requests. Default True |
| ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS | List of days users can request extensions in an allocation change request. Default 30,60,90 |
| ALLOCATION_ACCOUNT_ENABLED             | Allow user to select account name for allocation. Default False |
| ALLOCATION_RESOURCE_ORDERING           | Controls the ordering of parent resources for an allocation (if allocation has multiple resources).  Should be a list of field names suitable for Django QuerySet order_by method.  Default is ['-is_allocatable', 'name']; i.e. prefer Resources with is_allocatable field set, ordered by name of the Resource.|
| ALLOCATION_EULA_ENABLE                 | Enable or disable requiring users to agree to EULA on allocations. Only applies to allocations using a resource with a defined 'eula' attribute. Default False|
| INVOICE_ENABLED                        | Enable or disable invoices. Default True       |
| ONDEMAND_URL                           | The URL to your Open OnDemand installation     |
| LOGIN_FAIL_MESSAGE                     | Custom message when user fails to login. Here you can paint a custom link to your user account portal |
| ENABLE_SU                              | Enable administrators to login as other users. Default True |
| RESEARCH_OUTPUT_ENABLE                 | Enable or disable research outputs. Default True |
| GRANT_ENABLE                           | Enable or disable grants. Default True           |
| PUBLICATION_ENABLE                     | Enable or disable publications. Default True     |
| PROJECT_CODE                                 | Specifies a custom internal project identifier. Default False, provide string value to enable.|  
| PROJECT_CODE_PADDING                         | Defines a optional padding value to be added before the Primary Key section of PROJECT_CODE. Default False, provide integer value to enable.|
| PROJECT_INSTITUTION_EMAIL_MAP                | Defines a dictionary where PI domain email addresses are keys and their corresponding institutions are values. Default is False, provide key-value pairs to enable this feature.|  
### Database settings

The following settings configure the database server to use, if not set will default to using SQLite:

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| DB_URL               | The database connection url string   |

Examples:

```
DB_URL=mysql://user:password@127.0.0.1:3306/database
DB_URL=psql://user:password@127.0.0.1:5432/database
DB_URL=sqlite:////usr/share/coldfront/coldfront.db
```


### Email settings

The following settings configure emails in ColdFront. By default email is
disabled:

| Name                            | Description                               |
| :-------------------------------|:------------------------------------------|
| EMAIL_ENABLED                   | Enable/disable email. Default False       |
| EMAIL_HOST                      | Hostname of smtp server                   |
| EMAIL_PORT                      | smtp port                                 |
| EMAIL_HOST_USER                 | Username for smtp                         |
| EMAIL_HOST_PASSWORD             | password for smtp                         |
| EMAIL_USE_TLS                   | Enable/disable tls. Default False         |
| EMAIL_SENDER                    | Default sender email address              |
| EMAIL_SUBJECT_PREFIX            | Prefix to add to subject line             |
| EMAIL_ADMIN_LIST                | List of admin email addresses.            |
| EMAIL_TICKET_SYSTEM_ADDRESS     | Email address of ticketing system         |
| EMAIL_DIRECTOR_EMAIL_ADDRESS    | Email address for director                |
| EMAIL_PROJECT_REVIEW_CONTACT    | Email address of review contact           |
| EMAIL_DEVELOPMENT_EMAIL_LIST    | List of emails to send when in debug mode |
| EMAIL_OPT_OUT_INSTRUCTION_URL   | URL of article regarding opt out          |
| EMAIL_SIGNATURE                 | Email signature to add to outgoing emails |
| EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS   | List of days to send email notifications for expiring allocations. Default 7,14,30 |
| EMAIL_ADMINS_ON_ALLOCATION_EXPIRE | Setting this to True will send a daily email notification to administrators with a list of allocations that have expired that day. |
| EMAIL_ALLOCATION_EULA_REMINDERS | Enable/Disable EULA reminders. Default False |
| EMAIL_ALLOCATION_EULA_IGNORE_OPT_OUT | Ignore user email settings and always send EULA related emails. Default False |
| EMAIL_ALLOCATION_EULA_CONFIRMATIONS | Enable/Disable email notifications when a EULA is accepted or declined. Default False |
| EMAIL_ALLOCATION_EULA_CONFIRMATIONS_CC_MANAGERS | CC project managers on eula notification emails (requires EMAIL_ALLOCATION_EULA_CONFIRMATIONS to be enabled). Default False |
| EMAIL_ALLOCATION_EULA_INCLUDE_ACCEPTED_EULA | Include copy of EULA in email notifications for accepted EULAs. Default False |

### Plugin settings
For more info on [ColdFront plugins](plugin/existing_plugins.md) (Django apps)

#### LDAP Auth

!!! warning "Required"
    LDAP authentication backend requires `ldap3` and `django_auth_ldap`.
    ```
    $ pip install ldap3 django_auth_ldap
    ```

    This uses `django_auth_ldap` therefore ldaps cert paths will be taken from
    global OS ldap config, `/etc/{ldap,openldap}/ldap.conf` and within `TLS_CACERT`


| Name                        | Description                             |
| :---------------------------|:----------------------------------------|
| PLUGIN_AUTH_LDAP            | Enable LDAP Authentication Backend. Default False |
| AUTH_LDAP_SERVER_URI        | URI of LDAP server                      |
| AUTH_LDAP_START_TLS         | Enable/disable start tls. Default True  |
| AUTH_LDAP_BIND_DN           | The distinguished name to use when binding to the LDAP server      |
| AUTH_LDAP_BIND_PASSWORD     | The password to use AUTH_LDAP_BIND_DN   |
| AUTH_LDAP_USER_SEARCH_BASE  | User search base dn                     |
| AUTH_LDAP_GROUP_SEARCH_BASE | Group search base dn                    |
| AUTH_COLDFRONT_LDAP_SEARCH_SCOPE | The search scope for Coldfront authentication. Options: SUBTREE or default (ONELEVEL)   |
| AUTH_LDAP_MIRROR_GROUPS     | Enable/disable mirroring of groups. Default True  |
| AUTH_LDAP_BIND_AS_AUTHENTICATING_USER     | Authentication will leave the LDAP connection bound as the authenticating user, rather than forcing it to re-bind. Default False    |

#### OpenID Connect Auth

!!! warning "Required"
    OpenID Connect authentication backend requires `mozilla_django_oidc`.
    ```
    $ pip install mozilla_django_oidc
    ```
!!! warning "SESSION\_COOKIE\_SAMESITE"

    mozilla_django_oidc uses cookies to store state in an anonymous session during the
    authentication process. You must use `SESSION_COOKIE_SAMESITE="Lax"` in your
    settings for authentication to work correctly.

| Name                           | Description                          |
| :------------------------------|:-------------------------------------|
| PLUGIN_AUTH_OIDC               | Enable OpenID Connect Authentication Backend. Default False |
| OIDC_OP_JWKS_ENDPOINT          | URL of JWKS endpoint                 |
| OIDC_RP_SIGN_ALGO              | Signature algorithm                  |
| OIDC_RP_CLIENT_ID              | Client ID                            |
| OIDC_RP_CLIENT_SECRET          | Client secret                        |
| OIDC_OP_AUTHORIZATION_ENDPOINT | OAuth2 authorization endpoint        |
| OIDC_OP_TOKEN_ENDPOINT         | OAuth2 token endpoint                |
| OIDC_OP_USER_ENDPOINT          | OAuth2 userinfo endpoint             |
| OIDC_VERIFY_SSL                | Verify ssl Default True              |
| OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS | Token lifetime in seconds. Default 3600 |

#### Mokey

!!! warning "Required"
    Mokey depends on the OpenID Connect plugin above. You must also enable the
    OpenID Connect plugin via `PLUGIN_AUTH_OIDC=True`.

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| PLUGIN_MOKEY         | Enable Mokey/Hydra OpenID Connect Authentication Backend. Default False|

#### Slurm

| Name                  | Description                          |
| :---------------------|:-------------------------------------|
| PLUGIN_SLURM          | Enable Slurm integration. Default False |
| SLURM_SACCTMGR_PATH   | Path to sacctmgr command. Default `/usr/bin/sacctmgr` |
| SLURM_NOOP            | Enable/disable noop. Default False   |
| SLURM_IGNORE_USERS    | List of user accounts to ignore when generating Slurm associations |
| SLURM_IGNORE_ACCOUNTS | List of Slurm accounts to ignore when generating Slurm associations |

#### XDMoD

| Name                 | Description                             |
| :--------------------|:----------------------------------------|
| PLUGIN_XDMOD         | Enable XDMoD integration. Default False |
| XDMOD_API_URL        | URL to XDMoD API                        |

#### FreeIPA

| Name                     | Description                               |
| :------------------------|:------------------------------------------|
| PLUGIN_FREEIPA           | Enable FreeIPA integration. Default False |
| FREEIPA_KTNAME           | Path to keytab file                       |
| FREEIPA_SERVER           | Hostname of FreeIPA server                |
| FREEIPA_USER_SEARCH_BASE | User search base dn                       |
| FREEIPA_ENABLE_SIGNALS   | Enable/Disable signals. Default False     |

#### iquota

| Name            | Description                              |
| :---------------|:-----------------------------------------|
| PLUGIN_IQUOTA   | Enable iquota integration. Default False |
| IQUOTA_KEYTAB   | Path to keytab file                      |
| IQUOTA_CA_CERT  | Path to ca cert                          |
| IQUOTA_API_HOST | Hostname of iquota server                |
| IQUOTA_API_PORT | Port of iquota server                    |

#### LDAP User Search

This plugin allows searching for users via LDAP. This has nothing to do with
authentication. This allows users who haven't yet logged into ColdFront but
exist in your backend LDAP to show up in the ColdFront user search.

!!! warning "Required"
    LDAP User Search requires `ldap3`.
    ```
    $ pip install ldap3
    ```

| Name                        | Description                             |
| :---------------------------|:----------------------------------------|
| PLUGIN_LDAP_USER_SEARCH     | Enable LDAP User Search. Default False  |
| LDAP_USER_SEARCH_SERVER_URI | URI of LDAP server                      |
| LDAP_USER_SEARCH_BIND_DN    | The distinguished name to use when binding to the LDAP server      |
| LDAP_USER_SEARCH_BIND_PASSWORD  | The password to use LDAP_USER_SEARCH_BIND_DN   |
| LDAP_USER_SEARCH_BASE       | User search base dn                     |
| LDAP_USER_SEARCH_CONNECT_TIMEOUT  | Time in seconds to wait before timing out. Default 2.5  |
| LDAP_USER_SEARCH_USE_SSL  | Whether to use ssl when connecting to LDAP server. Default True |
| LDAP_USER_SEARCH_USE_TLS  | Whether to use tls when connecting to LDAP server. Default False |
| LDAP_USER_SEARCH_PRIV_KEY_FILE  | Path to the private key file.       |
| LDAP_USER_SEARCH_CERT_FILE  | Path to the certificate file.           |
| LDAP_USER_SEARCH_CACERT_FILE  | Path to the CA cert file.             |
| LDAP_USER_SEARCH_CERT_VALIDATE_MODE | Whether to require/validate certs.  If 'required', certs are required and validated.  If 'optional', certs are optional but validated if provided.  If 'none' (the default) certs are ignored. |

## Advanced Configuration

ColdFront uses the [Django
settings](https://docs.djangoproject.com/en/3.1/topics/settings/). In most
cases, you can set custom configurations via environment variables above. If
you need more control over the configuration you can create `/etc/coldfront/local_settings.py` 
or create a `local_settings.py` file in the coldfront project root 
to override any Django settings. Some examples:

Instead of setting the `DB_URL` environment variable, we can add a custom database configuration:

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

To authenticate against Active Directory, it's not uncommon to need 
the `OPT_REFERRALS` set to `0`. Likewise, we should look for users based 
on their `sAMAccountName` attribute, rather than `uid`.

```python
AUTH_LDAP_CONNECTION_OPTIONS={ldap.OPT_REFERRALS: 0}
AUTH_LDAP_BASE_DN = 'dc=example,dc=org' # same value as AUTH_LDAP_USER_SEARCH
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    AUTH_LDAP_BASE_DN, ldap.SCOPE_SUBTREE, '(sAMAccountName=%(user)s)')
```

Additional debug logging can be configured for troubleshooting. This example
attaches the `django_auth_ldap` logs to the primary Django logger so you 
can see debug those logs in your main log output.

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django_auth_ldap": {"level": "DEBUG", "handlers": ["console"]}
},
```

## Custom Branding

The default HTML templates and css can be easily customized to add your own
site specific branding or even modify the functionality of ColdFront. To
override the stock templates in ColdFront, create a directory and add your
custom templates. By default, ColdFront will look in
`/usr/share/coldfront/site/templates` and `/usr/share/coldfront/site/static`.
If you'd like to use a different directory then be sure to set the following
environment variable:

```
SITE_TEMPLATES=/path/to/your/templates
```

You can also override any static files such as CSS or images by creating a
directory and adding your custom static assets. Then set the following
environment variable:

```
SITE_STATIC=/path/to/static/files
```

To apply changes in a production environment (where the static files are served through an nginx or apache server), rerun `collectstatic`. Be sure to activate your virtual environment first if you're using one.
```sh
source /srv/coldfront/venv/bin/activate
coldfront collectstatic
```

As a simple example, to change the default background color from blue to black, create a common.css file with the following styles and set the SITE_STATIC environment variable when starting ColdFront:

```
$ mkdir -p site/static/common/css
$ tee site/static/common/css/common.css <<EOF
.bg-primary {
  background-color: #000 !important;
}
EOF

$ DEBUG=True SITE_STATIC=site/static coldfront runserver
```
