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

Note: You can check your project root with the following command:
```shell
coldfront diffsettings | grep PROJECT_ROOT
```

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

For [URL configurations](https://docs.djangoproject.com/en/dev/topics/http/urls/), you can create a python file to override ColdFront URLs:

- `local_urls.py` relative to coldfront.config package
- `/etc/coldfront/local_urls.py`
- `local_urls.py` in the ColdFront project root

You can also specify the path to `local_urls.py` using the
`COLDFRONT_URLS` environment variable. For example:

```
COLDFRONT_URLS=/opt/coldfront/myurls.py
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

| Name                       | Description                                                                                                                                                                                                                                                | Has Setting | Has Environment Variable |
| :------------------------- |:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------|:-------------------------|
| ALLOWED_HOSTS              | A list of strings representing the host/domain names that ColdFront can serve. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts)                                                                                               | no          | yes                      |
| DEBUG                      | Turn on/off debug mode. Never deploy a site into production with DEBUG turned on. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#debug)                                                                                                    | no          | yes                      |
| SECRET_KEY                 | This is used to provide cryptographic signing, and should be set to a unique, unpredictable value. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#secret-key). If you don't provide this one will be generated each time ColdFront starts. | no          | yes                      |
| LANGUAGE_CODE              | A string representing the language code. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#language-code)                                                                                                                                     | no          | yes                      |
| TIME_ZONE                  | A string representing the time zone for this installation. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-TIME_ZONE)                                                                                                           | no          | yes                      |
| Q_CLUSTER_RETRY            | The number of seconds Django Q broker will wait for a cluster to finish a task. [See here](https://django-q.readthedocs.io/en/latest/configure.html#retry)                                                                                                 | no          | yes                      |
| Q_CLUSTER_TIMEOUT          | The number of seconds a Django Q worker is allowed to spend on a task before it’s terminated. IMPORTANT NOTE: Q_CLUSTER_TIMEOUT must be less than Q_CLUSTER_RETRY. [See here](https://django-q.readthedocs.io/en/latest/configure.html#timeout)            | no          | yes                      |
| SESSION_INACTIVITY_TIMEOUT | Seconds of inactivity after which sessions will expire (default 1hr). This value sets the `SESSION_COOKIE_AGE` and the session is saved on every request. [See here](https://docs.djangoproject.com/en/4.1/topics/http/sessions/#when-sessions-are-saved)  | no          | yes                      |

### Template settings

| Name                 | Description                                                                                                                                                                                               | Has Setting | Has Environment Variable |
| :--------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------|:-------------------------|
| STATIC_ROOT          | Path to the directory where collectstatic will collect static files for deployment. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-STATIC_ROOT)                               | no          | yes                      |
| SITE_TEMPLATES       | Path to a directory of custom templates. Add custom templates here. This path will be added to TEMPLATES DIRS. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-TEMPLATES-DIRS) | no          | yes                      |
| SITE_STATIC          | Path to a directory of custom static files. Add custom css here. This path will be added to STATICFILES_DIRS [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-STATICFILES_DIRS) | no          | yes                      |

### ColdFront core settings

The following settings are ColdFront specific settings related to the core application.

| Name                                         | Description                                                                                           | Has Setting | Has Environment Variable |
|:---------------------------------------------|:------------------------------------------------------------------------------------------------------|:------------|:-------------------------|
| CENTER_NAME                                  | The display name of your center                                                                       | yes         | yes                      |
| CENTER_HELP_URL                              | The URL of your help ticketing system                                                                 | no          | yes                      |
| CENTER_PROJECT_RENEWAL_HELP_URL              | The URL of the article describing project renewals                                                    | yes         | yes                      |
| CENTER_BASE_URL                              | The base URL of your center.                                                                          | yes         | yes                      |
| PROJECT_ENABLE_PROJECT_REVIEW                | Enable or disable project reviews. Default True                                                       | yes         | yes                      |
| ALLOCATION_ENABLE_ALLOCATION_RENEWAL         | Enable or disable allocation renewals. Default True                                                   | yes         | yes                      |
| ALLOCATION_DEFAULT_ALLOCATION_LENGTH         | Default number of days an allocation is active for. Default 365                                       | yes         | yes                      |
| ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT | Enable or disable allocation change requests. Default True                                            | yes         | no                       |
| ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS     | List of days users can request extensions in an allocation change request. Default 30,60,90           | yes         | yes                      |
| ALLOCATION_ACCOUNT_ENABLED                   | Allow user to select account name for allocation. Default False                                       | yes         | yes                      |
| ALLOCATION_ACCOUNT_MAPPING | Mapping where each key is the name of a resource and each value is the name of the attribute where the account name will be stored in the allocation. Only applies when `ALLOCATION_ACCOUNT_ENABLE` is true. Default `{}` | yes | yes |
| ALLOCATION_RESOURCE_ORDERING | Controls the ordering of parent resources for an allocation (if allocation has multiple resources).  Should be a list of field names suitable for Django QuerySet order_by method.  Default is ['-is_allocatable', 'name']; i.e. prefer Resources with is_allocatable field set, ordered by name of the Resource. | yes | no |
| ALLOCATION_EULA_ENABLE | Enable or disable requiring users to agree to EULA on allocations. Only applies to allocations using a resource with a defined 'eula' attribute. Default False | yes | yes |
| ALLOCATION_ATTRIBUTE_VIEW_LIST               | Names of allocation attributes which should be viewed as a list                                       | yes         | yes                      |
| ALLOCATION_FUNCS_ON_EXPIRE                   | Functions to be called when an allocation expires                                                     | yes         | no                       |
| INVOICE_ENABLED                              | Enable or disable invoices. Default True                                                              | yes         | yes                      |
| ONDEMAND_URL                                 | The URL to your Open OnDemand installation                                                            | no          | yes                      |
| LOGIN_FAIL_MESSAGE                           | Custom message when user fails to login. Here you can paint a custom link to your user account portal | no          | yes                      |
| ENABLE_SU                                    | Enable administrators to login as other users. Default True                                           | no          | yes                      |
| RESEARCH_OUTPUT_ENABLE                       | Enable or disable research outputs. Default True                                                      | no          | yes                      |
| GRANT_ENABLE                                 | Enable or disable grants. Default True                                                                | no          | yes                      |
| PUBLICATION_ENABLE                           | Enable or disable publications. Default True                                                          | no          | yes                      |
| PROJECT_CODE | Specifies a custom internal project identifier. Default False, provide string value to enable. Must be no longer than 10 - PROJECT_CODE_PADDING characters in length. | yes | yes |
| PROJECT_CODE_PADDING | Defines a optional padding value to be added before the Primary Key section of PROJECT_CODE. Default False, provide integer value to enable. | yes | yes |
| PROJECT_INSTITUTION_EMAIL_MAP | Defines a dictionary where PI domain email addresses are keys and their corresponding institutions are values. Default is False, provide key-value pairs to enable this feature. | yes | yes |
| ACCOUNT_CREATION_TEXT                        |                                                                                                       | yes         | yes                      |
| ADDITIONAL_USER_SEARCH_CLASSES               |                                                                                                       | yes         | no                       |
| ADMIN_COMMENTS_SHOW_EMPTY                    |                                                                                                       | no          | yes                      |
| ALLOCATION_ENABLE_CHANGE_REQUESTS            |                                                                                                       | no          | yes                      |
| BASE_DIR                                     |                                                                                                       | yes         | no                       |
| COLDFRONT_CONFIG                             |                                                                                                       | no          | yes                      |
| COLDFRONT_ENV                                |                                                                                                       | no          | yes                      |
| COLDFRONT_URLS                               |                                                                                                       | no          | yes                      |
| INVOICE_DEFAULT_STATUS                       |                                                                                                       | yes         | yes                      |
| LOGOUT_REDIRECT_URL                          |                                                                                                       | no          | yes                      |
| PLUGIN_API                                   |                                                                                                       | no          | yes                      |
| PLUGIN_SYSMON                                |                                                                                                       | no          | yes                      |
| SYSMON_ENDPOINT                              | same as `SYSTEM_MONITOR_ENDPOINT`                                                                     | no          | yes                      |
| SYSMON_LINK                                  | same as `SYSTEM_MONITOR_DISPLAY_MORE_STATUS_INFO_LINK`                                                | no          | yes                      |
| SYSMON_TITLE                                 | same as `SYSTEM_MONITOR_PANEL_TITLE`                                                                  | no          | yes                      |
| SYSMON_XDMOD_LINK                            | same as `SYSTEM_MONITOR_DISPLAY_XDMOD_LINK`                                                           | no          | yes                      |
| SYSTEM_MONITOR_DISPLAY_MORE_STATUS_INFO_LINK |                                                                                                       | yes         | no                       |
| SYSTEM_MONITOR_DISPLAY_XDMOD_LINK            |                                                                                                       | yes         | no                       |
| SYSTEM_MONITOR_ENDPOINT                      |                                                                                                       | yes         | no                       |
| SYSTEM_MONITOR_PANEL_TITLE                   |                                                                                                       | yes         | no                       |
| TEMPLATES                                    |                                                                                                       | yes         | no                       |

### Database settings

The following settings configure the database server to use, if not set will default to using SQLite:

| Name                 | Description                        | Has Setting | Has Environment Variable |
| :--------------------|:-----------------------------------|:------------|:-------------------------|
| DB_URL               | The database connection url string | no          | yes                      |

Examples:

```
DB_URL=mysql://user:password@127.0.0.1:3306/database
DB_URL=psql://user:password@127.0.0.1:5432/database
DB_URL=sqlite:////usr/share/coldfront/coldfront.db
```


### Email settings

The following settings configure emails in ColdFront. By default email is
disabled:

| Name                                            | Description                                                                                                                        | Has Setting | Has Environment Variable |
| :-----------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------|:------------|:-------------------------|
| EMAIL_ENABLED                                   | Enable/disable email. Default False                                                                                                | yes         | yes                      |
| EMAIL_HOST                                      | Hostname of smtp server                                                                                                            | no          | yes                      |
| EMAIL_PORT                                      | smtp port                                                                                                                          | no          | yes                      |
| EMAIL_HOST_USER                                 | Username for smtp                                                                                                                  | no          | yes                      |
| EMAIL_HOST_PASSWORD                             | password for smtp                                                                                                                  | no          | yes                      |
| EMAIL_USE_TLS                                   | Enable/disable tls. Default False                                                                                                  | no          | yes                      |
| EMAIL_SENDER                                    | Default sender email address                                                                                                       | yes         | yes                      |
| EMAIL_SUBJECT_PREFIX                            | Prefix to add to subject line                                                                                                      | yes         | yes                      |
| EMAIL_ADMIN_LIST                                | List of admin email addresses.                                                                                                     | yes         | yes                      |
| EMAIL_TICKET_SYSTEM_ADDRESS                     | Email address of ticketing system                                                                                                  | yes         | yes                      |
| EMAIL_DIRECTOR_EMAIL_ADDRESS                    | Email address for director                                                                                                         | yes         | yes                      |
| EMAIL_PROJECT_REVIEW_CONTACT                    | Email address of review contact                                                                                                    | no          | yes                      |
| EMAIL_DEVELOPMENT_EMAIL_LIST                    | List of emails to send when in debug mode                                                                                          | yes         | yes                      |
| EMAIL_OPT_OUT_INSTRUCTION_URL                   | URL of article regarding opt out                                                                                                   | yes         | yes                      |
| EMAIL_SIGNATURE                                 | Email signature to add to outgoing emails                                                                                          | yes         | yes                      |
| EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS     | List of days to send email notifications for expiring allocations. Default 7,14,30                                                 | yes         | yes                      |
| EMAIL_ADMINS_ON_ALLOCATION_EXPIRE               | Setting this to True will send a daily email notification to administrators with a list of allocations that have expired that day. | yes         | yes                      |
| EMAIL_ALLOCATION_EULA_REMINDERS                 | Enable/Disable EULA reminders. Default False                                                                                       | no          | yes                      |
| EMAIL_ALLOCATION_EULA_IGNORE_OPT_OUT            | Ignore user email settings and always send EULA related emails. Default False                                                      | yes         | yes                      |
| EMAIL_ALLOCATION_EULA_CONFIRMATIONS             | Enable/Disable email notifications when a EULA is accepted or declined. Default False                                              | yes         | yes                      |
| EMAIL_ALLOCATION_EULA_CONFIRMATIONS_CC_MANAGERS | CC project managers on eula notification emails (requires EMAIL_ALLOCATION_EULA_CONFIRMATIONS to be enabled). Default False        | yes         | yes                      |
| EMAIL_ALLOCATION_EULA_INCLUDE_ACCEPTED_EULA     | Include copy of EULA in email notifications for accepted EULAs. Default False                                                      | yes         | yes                      |
| EMAIL_TIMEOUT                                   |                                                                                                                                    | no          | yes                      |
| EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL     |                                                                                                                                    | yes         | no                       |

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


| Name                                  | Description                                                                                                                      | Has Setting | Has Environment Variable |
| :-------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|:------------|:-------------------------|
| PLUGIN_AUTH_LDAP                      | Enable LDAP Authentication Backend. Default False                                                                                | no          | yes                      |
| AUTH_LDAP_SERVER_URI                  | URI of LDAP server                                                                                                               | no          | yes                      |
| AUTH_LDAP_START_TLS                   | Enable/disable start tls. Default True                                                                                           | no          | yes                      |
| AUTH_LDAP_BIND_DN                     | The distinguished name to use when binding to the LDAP server                                                                    | no          | yes                      |
| AUTH_LDAP_BIND_PASSWORD               | The password to use AUTH_LDAP_BIND_DN                                                                                            | no          | yes                      |
| AUTH_LDAP_USER_SEARCH_BASE            | User search base dn                                                                                                              | no          | yes                      |
| AUTH_LDAP_GROUP_SEARCH_BASE           | Group search base dn                                                                                                             | no          | yes                      |
| AUTH_COLDFRONT_LDAP_SEARCH_SCOPE      | The search scope for Coldfront authentication. Options: SUBTREE or default (ONELEVEL)                                            | no          | yes                      |
| AUTH_LDAP_MIRROR_GROUPS               | Enable/disable mirroring of groups. Default True                                                                                 | no          | yes                      |
| AUTH_LDAP_BIND_AS_AUTHENTICATING_USER | Authentication will leave the LDAP connection bound as the authenticating user, rather than forcing it to re-bind. Default False | no          | yes                      |
| AUTH_LDAP_USER_ATTR_MAP               |                                                                                                                                  | no          | yes                      |

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

| Name                               | Description                                                 | Has Setting | Has Environment Variable |
| :----------------------------------|:------------------------------------------------------------|:------------|:-------------------------|
| PLUGIN_AUTH_OIDC                   | Enable OpenID Connect Authentication Backend. Default False | no          | yes                      |
| OIDC_OP_JWKS_ENDPOINT              | URL of JWKS endpoint                                        | no          | yes                      |
| OIDC_RP_SIGN_ALGO                  | Signature algorithm                                         | no          | yes                      |
| OIDC_RP_CLIENT_ID                  | Client ID                                                   | no          | yes                      |
| OIDC_RP_CLIENT_SECRET              | Client secret                                               | no          | yes                      |
| OIDC_OP_AUTHORIZATION_ENDPOINT     | OAuth2 authorization endpoint                               | no          | yes                      |
| OIDC_OP_TOKEN_ENDPOINT             | OAuth2 token endpoint                                       | no          | yes                      |
| OIDC_OP_USER_ENDPOINT              | OAuth2 userinfo endpoint                                    | no          | yes                      |
| OIDC_VERIFY_SSL                    | Verify ssl Default True                                     | no          | yes                      |
| OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS | Token lifetime in seconds. Default 3600                     | no          | yes                      |

#### Mokey

!!! warning "Required"
    Mokey depends on the OpenID Connect plugin above. You must also enable the
    OpenID Connect plugin via `PLUGIN_AUTH_OIDC=True`.

| Name                      | Description                                                             | Has Setting | Has Environment Variable |
| :-------------------------|:------------------------------------------------------------------------|:------------|:-------------------------|
| PLUGIN_MOKEY              | Enable Mokey/Hydra OpenID Connect Authentication Backend. Default False | no          | yes                      |
| MOKEY_OIDC_ALLOWED_GROUPS |                                                                         | yes         | no                       |
| MOKEY_OIDC_DENY_GROUPS    |                                                                         | yes         | no                       |
| MOKEY_OIDC_PI_GROUP       |                                                                         | yes         | yes                      |

#### Slurm

| Name                            | Description                                                         | Has Setting | Has Environment Variable |
| :-------------------------------|:--------------------------------------------------------------------|:------------|:-------------------------|
| PLUGIN_SLURM                    | Enable Slurm integration. Default False                             | no          | yes                      |
| SLURM_SACCTMGR_PATH             | Path to sacctmgr command. Default `/usr/bin/sacctmgr`               | yes         | yes                      |
| SLURM_NOOP                      | Enable/disable noop. Default False                                  | yes         | yes                      |
| SLURM_IGNORE_USERS              | List of user accounts to ignore when generating Slurm associations  | yes         | yes                      |
| SLURM_IGNORE_ACCOUNTS           | List of Slurm accounts to ignore when generating Slurm associations | yes         | yes                      |
| SLURM_ACCOUNT_ATTRIBUTE_NAME    | Internal use only                                                   | yes         | no                       |
| SLURM_CLUSTER_ATTRIBUTE_NAME    | Internal use only                                                   | yes         | no                       |
| SLURM_IGNORE_CLUSTERS           | Internal use only                                                   | yes         | no                       |
| SLURM_SPECS_ATTRIBUTE_NAME      | Internal use only                                                   | yes         | no                       |
| SLURM_USER_SPECS_ATTRIBUTE_NAME | Internal use only                                                   | yes         | no                       |

#### XDMoD

| Name                                 | Description                             | Has Setting | Has Environment Variable |
| :------------------------------------|:----------------------------------------|:------------|:-------------------------|
| PLUGIN_XDMOD                         | Enable XDMoD integration. Default False | no          | yes                      |
| XDMOD_API_URL                        | URL to XDMoD API                        | yes         | yes                      |
| XDMOD_ACC_HOURS_ATTRIBUTE_NAME       | Internal use only                       | yes         | no                       |
| XDMOD_ACCOUNT_ATTRIBUTE_NAME         | Internal use only                       | yes         | no                       |
| XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME | Internal use only                       | yes         | no                       |
| XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME   | Internal use only                       | yes         | no                       |
| XDMOD_CPU_HOURS_ATTRIBUTE_NAME       | Internal use only                       | yes         | no                       |
| XDMOD_RESOURCE_ATTRIBUTE_NAME        | Internal use only                       | yes         | no                       |
| XDMOD_STORAGE_ATTRIBUTE_NAME         | Internal use only                       | yes         | no                       |
| XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME   | Internal use only                       | yes         | no                       |

#### FreeIPA

| Name                         | Description                               | Has Setting | Has Environment Variable |
| :----------------------------|:------------------------------------------|:------------|:-------------------------|
| PLUGIN_FREEIPA               | Enable FreeIPA integration. Default False | no          | yes                      |
| FREEIPA_KTNAME               | Path to keytab file                       | yes         | yes                      |
| FREEIPA_SERVER               | Hostname of FreeIPA server                | yes         | yes                      |
| FREEIPA_USER_SEARCH_BASE     | User search base dn                       | yes         | yes                      |
| FREEIPA_ENABLE_SIGNALS       | Enable/Disable signals. Default False     | yes         | no                       |
| FREEIPA_GROUP_ATTRIBUTE_NAME | Internal use only                         | yes         | no                       |
| FREEIPA_NOOP                 | Internal use only                         | yes         | no                       |

#### iquota

| Name            | Description                              | Has Setting | Has Environment Variable |
| :---------------|:-----------------------------------------|:------------|:-------------------------|
| PLUGIN_IQUOTA   | Enable iquota integration. Default False | no          | yes                      |
| IQUOTA_KEYTAB   | Path to keytab file                      | yes         | yes                      |
| IQUOTA_CA_CERT  | Path to ca cert                          | yes         | yes                      |
| IQUOTA_API_HOST | Hostname of iquota server                | yes         | yes                      |
| IQUOTA_API_PORT | Port of iquota server                    | yes         | yes                      |

#### LDAP User Search

This plugin allows searching for users via LDAP. This has nothing to do with
authentication. This allows users who haven't yet logged into ColdFront but
exist in your backend LDAP to show up in the ColdFront user search.

!!! warning "Required"
    LDAP User Search requires `ldap3`.
    ```
    $ pip install ldap3
    ```

| Name                                | Description                                                      | Has Setting | Has Environment Variable |
| :-----------------------------------|:-----------------------------------------------------------------|:------------|:-------------------------|
| PLUGIN_LDAP_USER_SEARCH             | Enable LDAP User Search. Default False                           | no          | yes                      |
| LDAP_USER_SEARCH_SERVER_URI         | URI of LDAP server                                               | yes         | yes                      |
| LDAP_USER_SEARCH_BIND_DN            | The distinguished name to use when binding to the LDAP server    | yes         | yes                      |
| LDAP_USER_SEARCH_BIND_PASSWORD      | The password to use LDAP_USER_SEARCH_BIND_DN                     | yes         | yes                      |
| LDAP_USER_SEARCH_BASE               | User search base dn                                              | yes         | yes                      |
| LDAP_USER_SEARCH_CONNECT_TIMEOUT    | Time in seconds to wait before timing out. Default 2.5           | yes         | yes                      |
| LDAP_USER_SEARCH_USE_SSL            | Whether to use ssl when connecting to LDAP server. Default True  | yes         | yes                      |
| LDAP_USER_SEARCH_USE_TLS            | Whether to use tls when connecting to LDAP server. Default False | yes         | yes                      |
| LDAP_USER_SEARCH_PRIV_KEY_FILE      | Path to the private key file.                                    | yes         | yes                      |
| LDAP_USER_SEARCH_CERT_FILE          | Path to the certificate file.                                    | yes         | yes                      |
| LDAP_USER_SEARCH_CACERT_FILE        | Path to the CA cert file.                                        | yes         | yes                      |
| LDAP_USER_SEARCH_CERT_VALIDATE_MODE | Whether to require/validate certs.  If 'required', certs are required and validated.  If 'optional', certs are optional but validated if provided.  If 'none' (the default) certs are ignored. | yes | yes |
| LDAP_USER_SEARCH_ATTRIBUTE_MAP      | Internal use only                                                | yes         | no                       |
| LDAP_USER_SEARCH_MAPPING_CALLBACK   | Internal use only                                                | yes         | no                       |
| LDAP_USER_SEARCH_SASL_CREDENTIALS   | Internal use only                                                | yes         | no                       |
| LDAP_USER_SEARCH_SASL_MECHANISM     | Internal use only                                                | yes         | no                       |
| LDAP_USER_SEARCH_USERNAME_ONLY_ATTR | Internal use only                                                | yes         | no                       |

#### Project OpenLDAP

This plugin allows for projects and project membership to be synced to an OpenLDAP server.
See `coldfront/coldfront/plugins/project_openldap/README.md` in the source code for more detailed information.

| Option                                      | Description                                                                          | Has Setting | Has Environment Variable |
| :-------------------------------------------|:-------------------------------------------------------------------------------------|:------------|:-------------------------|
| `PLUGIN_PROJECT_OPENLDAP`                   | Enable the plugin, required to be set as True (bool).                                | no          | yes                      |
| `PROJECT_OPENLDAP_GID_START`                | Starting value for project gidNumbers, requires an integer.                          | yes         | yes                      |
| `PROJECT_OPENLDAP_SERVER_URI`               | The URI of the OpenLDAP instance, requires a string URI.                             | yes         | yes                      |
| `PROJECT_OPENLDAP_OU`                       | The OU where projects will be written, requires a string DN of OU.                   | yes         | yes                      |
| `PROJECT_OPENLDAP_BIND_USER`                | DN of bind user.                                                                     | yes         | yes                      |
| `PROJECT_OPENLDAP_BIND_PASSWORD`            | The password for the bind user, requires a string.                                   | yes         | yes                      |
| `PROJECT_OPENLDAP_REMOVE_PROJECT`           | Required to take action upon archive (action) of a project. Default True (bool).     | yes         | yes                      |
| `PROJECT_OPENLDAP_CONNECT_TIMEOUT`          | Connection timeout.                                                                  | yes         | yes                      |
| `PROJECT_OPENLDAP_USE_SSL`                  | Use SSL.                                                                             | yes         | yes                      |
| `PROJECT_OPENLDAP_USE_TLS`                  | Enable Tls.                                                                          | yes         | yes                      |
| `PROJECT_OPENLDAP_PRIV_KEY_FILE`            | Tls Private key.                                                                     | yes         | yes                      |
| `PROJECT_OPENLDAP_CERT_FILE`                | Tls Certificate file.                                                                | yes         | yes                      |
| `PROJECT_OPENLDAP_CACERT_FILE`              | Tls CA certificate file.                                                             | yes         | yes                      |
| `PROJECT_OPENLDAP_ARCHIVE_OU`               | Destination OU for archived projects.                                                | yes         | yes                      |
| `PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH` | Truncates the project title before inserting it into the description LDAP attribute. | yes         | yes                      |
| `PROJECT_OPENLDAP_EXCLUDE_USERS`            | Exclude users from sync command.                                                     | yes         | yes                      |

#### Auto Compute Allocation

| Option                                                    | Description | Has Setting | Has Environment Variable |
| :---------------------------------------------------------|:------------|:-------------|:------------------------|
| PLUGIN_AUTO_COMPUTE_ALLOCATION                            |             | no          | yes                      |
| AUTO_COMPUTE_ALLOCATION_CHANGEABLE                        |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_CLUSTERS                          |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_CORE_HOURS                        |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING               |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_DESCRIPTION                       |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_END_DELTA                         |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION             |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_LOCKED                            |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS                 |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING        |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT         |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE                  |             | yes         | yes                      |
| AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING         |             | yes         | yes                      |

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
