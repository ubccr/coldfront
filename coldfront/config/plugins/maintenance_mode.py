from coldfront.config.base import MIDDLEWARE, INSTALLED_APPS
from coldfront.config.env import ENV


INSTALLED_APPS += [
    'coldfront.plugins.maintenance_mode',
]

MIDDLEWARE += [
    'coldfront.plugins.maintenance_mode.middleware.MaintenanceModeMiddleware'
]

MAINTENANCE_MODE_ENABLED = ENV.bool('MAINTENANCE_MODE_ENABLED', default=False)
MAINTENANCE_MODE_BYPASS_PASSWORD = ENV.str('MAINTENANCE_MODE_BYPASS_PASSWORD', default='')