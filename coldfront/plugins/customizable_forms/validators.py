import logging
from django.core.exceptions import ValidationError
from coldfront.plugins.ldap_user_info.utils import get_user_info
from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)


SLATE_PROJECT_INCOMING_DIR = import_from_settings('SLATE_PROJECT_INCOMING_DIR', '')


class ValidateNumberOfUsers():
    def __init__(self, limit, count_start=0):
        self.limit = limit
        self.count_start = count_start

    def __call__(self, value):
        count = self.count_start + len(value)
        if count > self.limit:
            raise ValidationError(f'This resource has a limit of {self.limit} users.', code='invalid')


class ValidateAccountNumber():
    def __call__(self, value):
        if not value:
            return

        if len(value) != 9:
            raise ValidationError(f'Format is not correct', code='invalid')

        if value[2] != '-' or value[6] != '-':
            raise ValidationError(f'Format is not correct', code='invalid')


class ValidateUsername():
    def __call__(self, value):
        if not value:
            return

        attribute = get_user_info(value, ['cn'])
        if not attribute.get('cn') or not attribute.get('cn')[0]:
            raise ValidationError('This username does not exist')
