from django.conf import settings
from django.utils.module_loading import import_string


"""Methods relating to billing ID validation. This module is modeled
after django.core.mail."""


__all__ = [
    'get_validator',
    'is_billing_id_valid',
]


def get_validator(backend=None, **kwds):
    klass = import_string(backend or settings.BILLING_VALIDATOR_BACKEND)
    return klass(**kwds)


def is_billing_id_valid(billing_id, validator=None):
    validator = validator or get_validator()
    return validator.is_billing_id_valid(billing_id)
