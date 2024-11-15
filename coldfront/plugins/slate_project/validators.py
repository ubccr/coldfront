import re
import logging
from django.core.exceptions import ValidationError
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.slate_project.utils import check_directory_name_duplicates, check_directory_name_format

logger = logging.getLogger(__name__)


SLATE_PROJECT_INCOMING_DIR = import_from_settings('SLATE_PROJECT_INCOMING_DIR', '')


class ValidateAccountNumber():
    def __call__(self, value):
        if not value:
            return

        if len(value) != 9:
            raise ValidationError(f'Format is not correct', code='invalid')

        if value[2] != '-' or value[6] != '-':
            raise ValidationError(f'Format is not correct', code='invalid')


class ValidateDirectoryName():
    def __call__(self, value):
        if not value:
            return

        is_valid_format = check_directory_name_format(value)
        if not is_valid_format:
            raise ValidationError(f'Contains invalid character(s)', code='invalid')


class ValidateDupDirectoryName():
    def __call__(self, value):
        if not value:
            return

        is_duplicate = check_directory_name_duplicates(value)
        if is_duplicate:
            raise ValidationError('This Slate Project directory name already exists', code='invalid')
