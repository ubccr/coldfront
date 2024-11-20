from pathlib import Path

import environ
from importlib.metadata import entry_points
from split_settings.tools import optional, include
from coldfront.config.env import ENV, PROJECT_ROOT

# ColdFront split settings
coldfront_configs = [
    'base.py',
    'database.py',
    'auth.py',
    'logging.py',
    'core.py',
    'email.py',
]

# ColdFront plugin settings
plugin_configs = {
    'PLUGIN_SLURM': 'plugins/slurm.py',
    'PLUGIN_IQUOTA': 'plugins/iquota.py',
    'PLUGIN_FREEIPA': 'plugins/freeipa.py',
    'PLUGIN_SYSMON': 'plugins/system_monitor.py',
    'PLUGIN_XDMOD': 'plugins/xdmod.py',
    'PLUGIN_AUTH_OIDC': 'plugins/openid.py',
    'PLUGIN_AUTH_LDAP': 'plugins/ldap.py',
    'PLUGIN_LDAP_USER_SEARCH': 'plugins/ldap_user_search.py',
}

# This allows plugins to be enabled via environment variables. Can alternatively
# add the relevant configs to local_settings.py
for key, pc in plugin_configs.items():
    if ENV.bool(key, default=False):
        coldfront_configs.append(pc)

# Local settings overrides
local_configs = [
    # Local settings relative to coldfront.config package
    'local_settings.py',

    # System wide settings for production deployments
    '/etc/coldfront/local_settings.py',

    # Local settings relative to coldfront project root
    PROJECT_ROOT('local_settings.py')
]

if ENV.str('COLDFRONT_CONFIG', default='') != '':
    # Local settings from path specified via environment variable
    local_configs.append(environ.Path(ENV.str('COLDFRONT_CONFIG'))())

for lc in local_configs:
    coldfront_configs.append(optional(lc))


# add settings from plugins in source tree
plugin_configs = list((Path(PROJECT_ROOT) / "coldfront/plugins").glob("*/settings.py"))
coldfront_configs.extend(plugin_configs)

include(*coldfront_configs)

from importlib import import_module

# import settings from pip installed
for entry_point in entry_points(group="coldfront_plugins").select(name="app"):
    try:
        plugin_settings = import_module(".settings", package=entry_point.value)
        globals().update(
            {attr: obj for attr, obj in vars(plugin_settings).items() if not attr.startswith('_')}
        )
    except ModuleNotFoundError:
        pass
