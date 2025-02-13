from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'coldfront.plugins.allocation_removal_requests',
]

ALLOCATION_REMOVAL_REQUESTS_ALLOWED = ENV.list('ALLOCATION_REMOVAL_REQUESTS_ALLOWED', default=[''])
