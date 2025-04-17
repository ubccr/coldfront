from coldfront.config.base import INSTALLED_APPS, ENV
from coldfront.config.env import ENV
from django.core.exceptions import ImproperlyConfigured



INSTALLED_APPS += [
    'coldfront.plugins.auto_compute_allocation',
]

AUTO_COMPUTE_ALLOCATION_END_DELTA = ENV.int('AUTO_COMPUTE_ALLOCATION_END_DELTA', default=365)
AUTO_COMPUTE_ALLOCATION_CHANGABLE = ENV.bool('AUTO_COMPUTE_ALLOCATION_CHANGABLE', default=True)
AUTO_COMPUTE_ALLOCATION_LOCKED = ENV.bool('AUTO_COMPUTE_ALLOCATION_LOCKED', default=False)
AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION = ENV.bool('AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION', default=False)
