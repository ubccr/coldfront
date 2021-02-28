import os
from split_settings.tools import optional, include
from coldfront.config.env import ENV, PROJECT_ROOT

# ColdFront split settings
coldfront_configs = [
    'base.py',
    'database.py',
    'auth.py',
    'email.py',
    'logging.py',
    'core.py',
]

# ColdFront plugin settings
plugin_configs = {
    'COLDFRONT_PLUGIN_SLURM_ENABLE': 'plugins/slurm.py',
    'COLDFRONT_PLUGIN_IQUOTA_ENABLE': 'plugins/iquota.py',
    'COLDFRONT_PLUGIN_FREEIPA_ENABLE': 'plugins/freeipa.py',
    'COLDFRONT_PLUGIN_MOKEY_ENABLE': 'plugins/mokey.py',
    'COLDFRONT_PLUGIN_SYSMON_ENABLE': 'plugins/system_montior.py',
    'COLDFRONT_PLUGIN_XDMOD_ENABLE': 'plugins/xdmod.py',
    'COLDFRONT_PLUGIN_OOD_ENABLE': 'plugins/ondemand.py',
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

     # XXX Deprecated. removing soon
    'local_strings.py',

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

include(*coldfront_configs)
