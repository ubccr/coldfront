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

| Name                 | Description                          |
| :--------------------|:-------------------------------------|
| ALLOWED_HOSTS        | A list of strings representing the host/domain names that ColdFront can serve. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts) |
| DEBUG                | Turn on/off debug mode. Never deploy a site into production with DEBUG turned on. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#debug) |
| SECRET_KEY           | This is used to provide cryptographic signing, and should be set to a unique, unpredictable value. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#secret-key). If you don't provide this one will be generated each time ColdFront starts. |
| LANGUAGE_CODE        | A string representing the language code. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#language-code)
| TIME_ZONE            | A string representing the time zone for this installation. [See here](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-TIME_ZONE) |
| Q_CLUSTER_RETRY    | The number of seconds Django Q broker will wait for a cluster to finish a task. [See here](https://django-q.readthedocs.io/en/latest/configure.html#retry) |
| Q_CLUSTER_TIMEOUT    | The number of seconds a Django Q worker is allowed to spend on a task before it’s terminated. IMPORTANT NOTE: Q_CLUSTER_TIMEOUT must be less than Q_CLUSTER_RETRY. [See here](https://django-q.readthedocs.io/en/latest/configure.html#timeout) |

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
| INVOICE_ENABLED                        | Enable or disable invoices. Default True       |
| ONDEMAND_URL                           | The URL to your Open OnDemand installation     |
| LOGIN_FAIL_MESSAGE                     | Custom message when user fails to login. Here you can paint a custom link to your user account portal |
| ENABLE_SU                              | Enable administrators to login as other users. Default True |

| [ORGANIZATION_PROJECT_DISPLAY_MODE](manual/organizations/configuration.md#ORGANIZATION_PROJECT_DISPLAY_MODE)      | Should Organizations appear on Project pages ['always', 'never', or 'not-empty' (default)] |
| [ORGANIZATION_USER_DISPLAY_MODE](manual/organizations/configuration.md#ORGANIZATION_USER_DISPLAY_MODE)      | Like ORGANIZATION_PROJECT_DISPLAY_MODE but for User pages |
| [ORGANIZATION_PROJECT_DISPLAY_TITLE](manual/organizations/configuration.md#ORGANIZATION_PROJECT_DISPLAY_TITLE)     | Title for Organization display on Project pages (Default 'Departments(s), etc.') |
| [ORGANIZATION_USER_DISPLAY_TITLE](manual/organizations/configuration.md#ORGANIZATION_USER_DISPLAY_TITLE)     | Like ORGANIZATION_PROJECT_DISPLAY_TITLE but for User pages |
| [ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT](manual/organizations/configuration.md#ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT)   | Boolean: Should PI be able to edit Organizations for their projects |

| [ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS](manual/organizations/configuration.md#ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS) | Boolean. If True, autopopulate Organizations from LDAP when user logs in.  Ignored unless PLUGIN_LDAP_AUTH is True |
| [ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE](manual/organizations/configuration.md#ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE) | LDAP attribute used for determining Organization membership for users |
| [ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE](manual/organizations/configuration.md#ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE) | LDAP attribute used for determining primary Organization membership for users |
| [ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS](manual/organizations/configuration.md#ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS) | Boolean. If True, create placeholder Organizations when encounter an unrecognized Organization string from LDAP |
| [ORGANIZATION_LDAP_USER_DELETE_MISSING](manual/organizations/configuration.md#ORGANIZATION_LDAP_USER_DELETE_MISSING) | Boolean. If True, remove Organizations for User if not present in LDAP |


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

### Plugin settings
For more info on [ColdFront plugins](plugin.md) (Django apps)

#### LDAP Auth

!!! warning "Required"
    LDAP authentication backend requires `ldap3` and `django_auth_ldap`.
    ```
    $ pip install ldap3 django_auth_ldap
    ```

| Name                        | Description                             |
| :---------------------------|:----------------------------------------|
| PLUGIN_AUTH_LDAP            | Enable LDAP Authentication Backend. Default False |
| AUTH_LDAP_SERVER_URI        | URI of LDAP server                      |
| AUTH_LDAP_START_TLS         | Enable/disable start tls. Default True  |
| AUTH_LDAP_BIND_DN           | The distinguished name to use when binding to the LDAP server      |
| AUTH_LDAP_BIND_PASSWORD     | The password to use AUTH_LDAP_BIND_DN   |
| AUTH_LDAP_USER_SEARCH_BASE  | User search base dn                     |
| AUTH_LDAP_GROUP_SEARCH_BASE | Group search base dn                    |
| AUTH_LDAP_MIRROR_GROUPS     | Enable/disable mirroring of groups. Default True  |
| AUTH_LDAP_BIND_AS_AUTHENTICATING_USER     | Authentication will leave the LDAP connection bound as the authenticating user, rather than forcing it to re-bind. Default False    |

#### OpenID Connect Auth

!!! warning "Required"
    OpenID Connect authentication backend requires `mozilla_django_oidc`.
    ```
    $ pip install mozilla_django_oidc
    ```

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

| Name                                          | Description                             |
| :---------------------------------------------|:----------------------------------------|
| PLUGIN_XDMOD                                  | Enable XDMoD integration. Default False |
| XDMOD_API_URL                                 | URL to XDMoD API                        |
| XDMOD_ACCOUNT_ATTRIBUTE_NAME                  | ??? Defaults to 'slurm_account_name'    |
| XDMOD_RESOURCE_ATTRIBUTE_NAME                 | ??? Defaults to 'xdmod_resource'        |
| XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME            | ??? Defaults to 'Cloud Account Name'    |
| XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME          | ??? Defaults to 'Core Usage (Hours)'    |
| XDMOD_CPU_HOURS_ATTRIBUTE_NAME                | ??? Defaults to 'Core Usage (Hours)'    |

| [XDMOD_MAX_HIERARCHY_TIERS](manual/organizations/xdmod.md#XDMod-Hierarchy-Tiers)| The number of tiers in XdMod hierarchy. Default is 3 |
| [XDMOD_ALLOCATION_IN_HIERARCHY](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If set, lowest tier is Allocations. Default false |
| [XDMOD_ALLOCATION_HIERARCHY_LABEL](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If allocations in hierarchy, this is the label for hierarchy.json |
| [XDMOD_ALLOCATION_HIERARCHY_INFO](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If allocations in hierarchy, this is the info for hierarchy.json |
| [XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If allocs in hier, this is the AllocAttribType to use for getting the code|
| [XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If allocs in hier, this is the AllocAttribType to use for getting the name|
| [XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If alloc code defaulted from Slurm account, this prefix added|
| [XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX](manual/organizations/xdmod.md#Including-Allocations-in-XDMod-Hierarchies)| If alloc code defaulted from Slurm account, this suffix added|
| [XDMOD_PROJECT_IN_HIERARCHY](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)| If set, have Project as a tier in XdMod hierarchy|
| [XDMOD_PROJECT_HIERARCHY_LABEL](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)| If proj in hier, this is the label for hierarchy.json|
| [XDMOD_PROJECT_HIERARCHY_INFO](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)| If proj in hier, this is the info for hierarchy.json|
| [XDMOD_PROJECT_HIERARCHY_CODE_MODE](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)| If proj in hier, this determines how the code value is generated| 
| [XDMOD_PROJECT_HIERARCHY_CODE_PREFIX](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)|If proj in hier, this is prefixed to basename for code in some cases|
| [XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)|If proj in hier, this is suffixed to basename for code in some cases|
| [XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME](manual/organizations/xdmod.md#Including-Projects-in-XDMoD-Hierarchies)|If proj in hier, this the AllocationAttributeType used for getting code name in some cases|
| [XDMOD_NAMES_CSV_USER_FNAME_FORMAT](manual/organizations/xdmod.md#Generating-names.csv)|This is used for generating the first name field in names.csv|
| [XDMOD_NAMES_CSV_USER_LNAME_FORMAT](manual/organizations/xdmod.md#Generating-names.csv)|This is used for generating the last name field in names.csv|

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
