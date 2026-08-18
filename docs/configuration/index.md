---
icon: lucide/sliders-horizontal
---

# Configuration

ColdFront uses [django-environ](https://django-environ.readthedocs.io/)
for configuration. Settings can come from environment variables, an
environment file, or a Python file.

## Configuration Methods

### Environment Files

ColdFront reads environment variables from these files in order:

1. `COLDFRONT_ENV` environment variable (path to a custom env file)
2. `.env` in the project root directory
3. `/etc/coldfront/coldfront.env`

Environment files use the standard `KEY=value` format.

### Local Settings

ColdFront loads Python configuration files in this order:

1. `local_settings.py` in the `coldfront.config` package
2. `/etc/coldfront/local_settings.py`
3. `local_settings.py` in the project root directory
4. A path specified by the `COLDFRONT_CONFIG` environment variable

Local settings files can override any Django or ColdFront setting using
standard Python assignment.

## Base Settings

These settings are defined in `src/coldfront/config/base.py`.

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `False` | Enable debug mode for development |
| `ALLOWED_HOSTS` | `[]` | List of allowed hostnames. Required in production |
| `SECRET_KEY` | Auto-generated | Django secret key. Required in production |
| `LANGUAGE_CODE` | `en-us` | Default language |
| `TIME_ZONE` | `America/New_York` | Server time zone |
| `SITE_TEMPLATES` | `""` | Path to custom template directory |
| `SITE_STATIC` | `""` | Path to custom static files directory |
| `STATIC_ROOT` | `static_root` | Directory for collected static files |
| `DJANGO_VITE_DEV_MODE` | `False` | Enable Vite dev server mode |
| `DJANGO_VITE_SERVER_PORT` | `5173` | Vite dev server port |
| `COLDFRONT_TASKS_BACKEND` | `django_tasks_db.backend.DatabaseBackend` | Background task backend. Use `django_tasks_rq.backend.RQBackend` for Redis |

## Database Settings

These settings are defined in `src/coldfront/config/database.py`.

| Variable | Default | Description |
|---|---|---|
| `DB_URL` | `sqlite:///coldfront.db` | Database URL. Supports `mysql://`, `psql://`, or `sqlite://` formats |

## Authentication Settings

These settings are defined in `src/coldfront/config/auth.py`.

| Variable | Default | Description |
|---|---|---|
| `LOGIN_URL` | `/login` | Login page URL |
| `LOGIN_REDIRECT_URL` | `/` | Redirect destination after login |
| `LOGOUT_REDIRECT_URL` | Login URL | Redirect destination after logout |
| `CSRF_TRUSTED_ORIGINS` | `[]` | List of trusted origins for CSRF |
| `SESSION_INACTIVITY_TIMEOUT` | `3600` | Session timeout in seconds |
| `API_TOKEN_PEPPERS` | `{}` | Peppers for API token hashing. Required in production |

### Remote User Authentication

| Variable | Default | Description |
|---|---|---|
| `REMOTE_AUTH_ENABLED` | `False` | Enable remote user authentication |
| `REMOTE_AUTH_BACKEND` | `coldfront.auth.RemoteUserBackend` | Remote auth backend class |
| `REMOTE_AUTH_HEADER` | `HTTP_REMOTE_USER` | Header for remote user identity |
| `REMOTE_AUTH_AUTO_CREATE_USER` | `False` | Auto-create users on first login |
| `REMOTE_AUTH_AUTO_CREATE_GROUPS` | `False` | Auto-create groups from headers |
| `REMOTE_AUTH_DEFAULT_GROUPS` | `[]` | Default groups for new users |
| `REMOTE_AUTH_DEFAULT_PERMISSIONS` | `{}` | Default permissions for new users |
| `REMOTE_AUTH_GROUP_HEADER` | `HTTP_REMOTE_USER_GROUP` | Header for group info |
| `REMOTE_AUTH_GROUP_SEPARATOR` | `\|` | Separator for group values |
| `REMOTE_AUTH_GROUP_SYNC_ENABLED` | `False` | Sync groups from headers on each login |
| `REMOTE_AUTH_SUPERUSER_GROUPS` | `[]` | Groups that grant superuser status |
| `REMOTE_AUTH_SUPERUSERS` | `[]` | Usernames that get superuser status |
| `REMOTE_AUTH_USER_EMAIL` | `HTTP_REMOTE_USER_EMAIL` | Header for user email |
| `REMOTE_AUTH_USER_FIRST_NAME` | `HTTP_REMOTE_USER_FIRST_NAME` | Header for first name |
| `REMOTE_AUTH_USER_LAST_NAME` | `HTTP_REMOTE_USER_LAST_NAME` | Header for last name |

### LDAP Authentication

| Variable | Default | Description |
|---|---|---|
| `AUTH_LDAP_SERVER_URI` | `None` | LDAP server URI |
| `AUTH_LDAP_USER_DN_TEMPLATE` | `None` | User DN template |
| `AUTH_LDAP_START_TLS` | `False` | Enable STARTTLS |
| `AUTH_LDAP_BIND_DN` | `None` | Bind DN for LDAP |
| `AUTH_LDAP_BIND_PASSWORD` | `None` | Bind password |
| `AUTH_LDAP_BIND_AS_AUTHENTICATING_USER` | `False` | Bind as authenticating user |
| `AUTH_LDAP_REQUIRE_GROUP` | `None` | Require membership in this group |
| `AUTH_LDAP_DENY_GROUP` | `None` | Deny access to this group |
| `AUTH_LDAP_MIRROR_GROUPS` | `True` | Mirror LDAP groups to ColdFront |
| `AUTH_LDAP_USER_FLAGS_BY_GROUP` | `{}` | User flags based on group membership |
| `LDAP_SEARCH_SCOPE` | `onelevel` | LDAP search scope |
| `LDAP_IGNORE_CERT_ERRORS` | `False` | Ignore TLS certificate errors |
| `LDAP_USER_SEARCH_BASE` | `None` | Base DN for user searches |
| `LDAP_USER_SEARCH_QUERY` | `(uid=%(user)s)` | User search filter |
| `LDAP_GROUP_SEARCH_BASE` | `None` | Base DN for group searches |
| `LDAP_GROUP_SEARCH_QUERY` | `(objectClass=groupOfNames)` | Group search filter |

### Social Authentication (OIDC, SSO)

| Variable | Default | Description |
|---|---|---|
| `SOCIAL_AUTH_BACKEND_ATTRS` | `{}` | Backend-specific attributes |
| `SOCIAL_AUTH_MIRROR_GROUPS` | `True` | Mirror SSO groups to ColdFront |

## Core Settings

These settings are defined in `src/coldfront/config/core.py`.

| Variable | Default | Description |
|---|---|---|
| `CENTER_NAME` | `HPC Center` | Name of your center |
| `CENTER_HELP_URL` | `""` | URL for help documentation |
| `CHANGELOG_RETENTION` | `90` | Days to retain change log records. Set to 0 to keep forever |
| `JOB_COMPLETED_RETENTION` | `90` | Days to retain completed job records |
| `JOB_FAILED_RETENTION` | `90` | Days to retain failed job records |
| `ACCEPTED_INVITE_RETENTION` | `90` | Days to retain accepted project invites. Expired invites are always deleted |
| `PAGINATE_COUNT` | `50` | Default page size for list views |
| `MAX_PAGE_SIZE` | `1000` | Maximum page size for API |
| `ALLOCATION_EXTENSION_REQUESTABLE_FIELDS` | `{}` | Fields users can request for allocation extensions |
| `FIELD_CHOICES` | `{}` | Custom field choices from environment |
| `AUTO_SLUG_FUNC` | `coldfront.models.utils.auto_generate_slug` | Slug generation function |
| `SYSTEM_NOTIFICATION_USERS` | `[]` | Additional users for system notifications |
| `SYSTEM_NOTIFICATION_GROUPS` | `[]` | Additional groups for system notifications |
| `DEFAULT_USER_PREFERENCES` | `{}` | Default preferences for new users |
| `INVITE_CODE_EXPIRE_SECONDS` | `86400` |  Number of seconds that a ProjectInvite code remains valid |

### Default Permissions

The `DEFAULT_PERMISSIONS` setting defines baseline permissions for all
users. These control what users can see and do by default:

- Users can manage their own API tokens
- Users can view all resources that are not locked
- Users can view projects they own or are a member of
- Users can view allocations they own or that belong to their projects

## Email Settings

These settings are defined in `src/coldfront/config/email.py`.

| Variable | Default | Description |
|---|---|---|
| `EMAIL_ENABLED` | `False` | Enable email notifications |
| `EMAIL_HOST` | `localhost` | SMTP server host |
| `EMAIL_PORT` | `25` | SMTP server port |
| `EMAIL_HOST_USER` | `""` | SMTP username |
| `EMAIL_HOST_PASSWORD` | `""` | SMTP password |
| `EMAIL_USE_TLS` | `False` | Use TLS for SMTP |
| `EMAIL_TIMEOUT` | `3` | SMTP timeout in seconds |
| `EMAIL_SUBJECT_PREFIX` | `[ColdFront]` | Subject prefix for emails |
| `EMAIL_SENDER` | `""` | Sender email address |
| `EMAIL_SIGNATURE` | `""` | Email signature |

## Slurm Settings

These settings are defined in `src/coldfront/config/slurm.py`.

| Variable | Default | Description |
|---|---|---|
| `COLDFRONT_SLURMRD_CLUSTERS` | See below | Per-cluster slurmrestd connection settings |
| `COLDFRONT_SLURM_AUTO_SYNC_ENABLED` | `False` | Enable automatic Slurm sync |
| `COLDFRONT_SLURM_SYNC_INTERVAL` | `1440` | Sync interval in minutes (default: daily) |

Per-cluster connection settings use a dictionary format. Each cluster can
have its own settings or use the `"default"` entry:

```python
COLDFRONT_SLURMRESTD_CLUSTERS = {
    "default": {
        "url": "http://slurmrestd:8080",
        "jwt_token": "",
        "api_version": "",
        "auth_type": "jwt",
        "timeout": 30,
        "retries": 3,
        "retry_backoff": 1.5,
        "auto_sync_enabled": False,
    },
}
```

## Plugin Settings

These settings are defined in `src/coldfront/config/plugins.py`.

| Variable | Default | Description |
|---|---|---|
| `PLUGINS` | `[]` | List of plugin names to load |
| `PLUGINS_CONFIG` | `{}` | Per-plugin configuration settings |
| `PLUGINS_CATALOG_CONFIG` | `{}` | Plugin catalog configuration |

## Redis Queue Settings

These settings are defined in `src/coldfront/config/base.py`.

| Variable | Default | Description |
|---|---|---|
| `RQ_REDIS_HOST` | `localhost` | Redis host |
| `RQ_REDIS_PORT` | `6379` | Redis port |
| `RQ_REDIS_DATABASE` | `8` | Redis database number |
| `RQ_REDIS_USERNAME` | `""` | Redis username |
| `RQ_REDIS_PASSWORD` | `""` | Redis password |
| `RQ_DEFAULT_TIMEOUT` | `300` | Default job timeout in seconds |

## Using local_settings.py

For advanced configuration, create a `local_settings.py` file. This is a
standard Python file that can override any Django or ColdFront setting.
Place it in one of these locations:

- `src/coldfront/config/local_settings.py` (relative to the config package)
- `/etc/coldfront/local_settings.py` (system-wide)
- `local_settings.py` in the project root directory

Example local_settings.py:

```python
# Override the center name
CENTER_NAME = "My HPC Center"

# Add a custom app
INSTALLED_APPS += [
    "my_custom_plugin",
]

# Configure Slurm connection
COLDFRONT_SLURMRESTD_CLUSTERS = {
    "default": {
        "url": "http://slurmrestd:8080",
        "jwt_token": "eyJhbGci...",
        "auto_sync_enabled": True,
    },
}
```
