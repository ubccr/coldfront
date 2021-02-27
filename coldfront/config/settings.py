import environ
from split_settings.tools import optional, include

ENV = environ.Env()
PROJECT_ROOT = environ.Path(__file__) - 3

# Default paths to environment files
configPaths = [
    PROJECT_ROOT.path('.env'),
    environ.Path('/etc/coldfront/coldfront.env'),
]

if ENV.str('COLDFRONT_ENV', default='') != '':
    configPaths.insert(0, environ.Path(ENV.str('COLDFRONT_ENV')))

for cfg in configPaths:
    try:
        cfg.file('')
        ENV.read_env(cfg())
    except FileNotFoundError:
        pass

coldfront_configs = [
    'base.py',
    'database.py',
    'auth.py',
    'email.py',
    'logging.py',
    'core.py',

    optional('local_settings.py'),

    # XXX Deprecated. removing soon
    optional('local_strings.py'),

    # Allow system wide settings for production deployments
    optional('/etc/coldfront/local_settings.py'),
]

if ENV.bool('COLDFRONT_PLUGIN_SLURM_ENABLE', default=False):
    coldfront_configs.append('plugins/slurm.py')

if ENV.bool('COLDFRONT_PLUGIN_IQUOTA_ENABLE', default=False):
    coldfront_configs.append('plugins/iquota.py')

if ENV.bool('COLDFRONT_PLUGIN_FREEIPA_ENABLE', default=False):
    coldfront_configs.append('plugins/freeipa.py')

if ENV.bool('COLDFRONT_PLUGIN_MOKEY_ENABLE', default=False):
    coldfront_configs.append('plugins/mokey.py')

if ENV.bool('COLDFRONT_PLUGIN_SYSMON_ENABLE', default=False):
    coldfront_configs.append('plugins/system_montior.py')

if ENV.bool('COLDFRONT_PLUGIN_XDMOD_ENABLE', default=False):
    coldfront_configs.append('plugins/xdmod.py')

if ENV.bool('COLDFRONT_PLUGIN_OOD_ENABLE', default=False):
    coldfront_configs.append('plugins/ondemand.py')

include(*coldfront_configs)
