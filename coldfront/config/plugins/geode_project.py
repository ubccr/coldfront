from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'coldfront.plugins.geode_project',
]

GEODE_PROJECT_EMAIL = ENV.str('GEODE_PROJECT_EMAIL')
