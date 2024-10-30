import re
from django.core.exceptions import ValidationError
from coldfront.plugins.ldap_user_info.utils import get_user_info
from coldfront.core.allocation.models import AllocationAttribute

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


class ValidateDirectoryName():
    def is_underscore(self, char):
        return char == '_'

    def __call__(self, value):
        if re.search('^[0-9a-zA-Z_-]+$', value) is None:
            raise ValidationError(f'Contains invalid character(s)', code='invalid')


class ValidateUsername():
    def __call__(self, value):
        if not value:
            return

        attribute = get_user_info(value, ['cn'])
        if not attribute.get('cn') or not attribute.get('cn')[0]:
            raise ValidationError('This username does not exist')


class ValidateDupDirectoryName():
    def __call__(self, value):
        if not value:
            return
        
        directory_names = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Slate Project Directory'
        ).values_list('value', flat=True)
        for directory_name in directory_names:
            if directory_name == value:
                raise ValidationError('This Slate Project directory name already exists')