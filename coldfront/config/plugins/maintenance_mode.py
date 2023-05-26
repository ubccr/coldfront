from coldfront.config.base import MIDDLEWARE, INSTALLED_APPS


INSTALLED_APPS += [
    'coldfront.plugins.maintenance_mode',
]

MIDDLEWARE += [
    'coldfront.plugins.maintenance_mode.middleware.MaintenanceModeMiddleware'
]
