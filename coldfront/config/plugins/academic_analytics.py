from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV


INSTALLED_APPS += [
    'coldfront.plugins.academic_analytics',
]

ACADEMIC_ANALYTICS_API_KEY = ENV.str('ACADEMIC_ANALYTICS_API_KEY')
ACADEMIC_ANALYTICS_API_BASE_ADDRESS = ENV.str('ACADEMIC_ANALYTICS_API_BASE_ADDRESS')