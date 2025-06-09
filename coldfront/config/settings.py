import environ
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
    'plugins/cas_login.py',
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
    'PLUGIN_LDAP_USER_INFO': 'plugins/ldap_user_info.py',
    'PLUGIN_CAS': 'plugins/cas_login.py',
    'PLUGIN_ACADEMIC_ANALYTICS': 'plugins/academic_analytics.py',
    'PLUGIN_ADVANCED_SEARCH': 'plugins/advanced_search.py',
    'PLUGIN_MAINTENANCE_MODE': 'plugins/maintenance_mode.py',
    'PLUGIN_UPDATE_USER_PROFILES': 'plugins/update_user_profiles.py',
    'PLUGIN_COLDFRONT_CUSTOM_RESOURCES': 'plugins/coldfront_custom_resources.py',
    'PLUGIN_CUSTOMIZABLE_FORMS': 'plugins/customizable_forms.py',
    'PLUGIN_PI_SEARCH': 'plugins/pi_search.py',
    'PLUGIN_ALLOCATION_REMOVAL_REQUESTS':'plugins/allocation_removal_requests.py',
    'PLUGIN_ANNOUNCEMENTS': 'plugins/announcements.py',
    'PLUGIN_MOVABLE_ALLOCATIONS': 'plugins/movable_allocations.py',
    'PLUGIN_HELP': 'plugins/help.py'
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

include(*coldfront_configs)
