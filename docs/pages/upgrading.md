# Upgrading

This document describes upgrading ColdFront. New releases of ColdFront may
introduce breaking changes so please refer to this document before upgrading.

## v1.1.3

This release changes some css/javascript assets to be hosted statically instead
of using a CDN. We also made some minor modifications to the default template.
This will require running collectstatic. Before upgrading, be sure to backup
your database and verify your custom template changes as they may need
updating. 

To upgrade via pip, following these steps:

```
$ source /path/to/your/venv/bin/activate
$ pip install --upgrade coldfront
$ coldfront migrate
$ coldfront collectstatic
```

## v1.1.2

This release includes a new notes field on projects which will require database
migrations. See [PR #403](https://github.com/ubccr/coldfront/pull/403) for
details. Before upgrading, be sure to backup your database and any custom
changes. 

To upgrade via pip, following these steps:

```
$ source /path/to/your/venv/bin/activate
$ pip install --upgrade coldfront
$ coldfront migrate
$ coldfront collectstatic
```

## v1.1.0

This release includes a new allocation change workflow along with a major
Django upgrade from v2.2 to v3.2, both of which will require database
migrations. Before upgrading, be sure to backup your database and any custom
changes. 

To upgrade via pip, following these steps:

```
$ source /path/to/your/venv/bin/activate
$ pip install --upgrade coldfront
$ coldfront migrate
$ coldfront collectstatic

# Optionally, add new default Resource Attribute Types
$ coldfront add_resource_defaults
```

## v1.0.3

This release changed the way ColdFront is configured. Before, there were two
files `local_settings.py` and `local_strings.py` that were used for custom
configuration settings. This release now uses environment variables. For more
details please see the documentation on [configuring ColdFront](config.md).
After upgrading to `v1.0.3` you'll need to migrate any custom configs to use
environment variables or modify your existing `local_settings.py` to conform to
the new settings. Here's a simple example of a `local_settings.py` file prior
to `v1.0.3`:

```python
EXTRA_APPS += [
    'coldfront.plugins.slurm',
]
SLURM_IGNORE_USERS = ['root']
SLURM_SACCTMGR_PATH = '/usr/bin/sacctmgr'
```

After upgrading to `v1.0.3` you'll need to modify your `local_settings.py` file
as follows:

```python
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [
    'coldfront.plugins.slurm',
]

SLURM_IGNORE_USERS = ['root']
SLURM_SACCTMGR_PATH = '/usr/bin/sacctmgr'
```

Or change to using environment variables:

```
PLUGIN_SLURM=True
SLURM_IGNORE_USERS=root,admin,testuser
SLURM_SACCTMGR_PATH=/usr/bin/sacctmgr
```
