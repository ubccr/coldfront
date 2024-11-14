import re
import os
import csv
import logging
from django.core.exceptions import ValidationError
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.utils.common import import_from_settings

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
        if re.search('^[0-9a-zA-Z_-]+$', value) is None:
            raise ValidationError(f'Contains invalid character(s)', code='invalid')


class ValidateDupDirectoryName():
    def __call__(self, value):
        if not value:
            return

        directory_value = '/N/project/' + value
        directory_names = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Slate Project Directory'
        ).values_list('value', flat=True)
        for directory_name in directory_names:
            if directory_name == directory_value:
                raise ValidationError('This Slate Project directory name already exists')

        if not os.path.isfile(os.path.join(SLATE_PROJECT_INCOMING_DIR, 'slate_projects.txt')):
            logger.warning('allocated_quantity.csv is missing. Skipping additional directory name checking')
            return

        with open(os.path.join(SLATE_PROJECT_INCOMING_DIR, 'allocated_quantity.csv'), 'r') as slate_projects:
            csv_reader = csv.reader(slate_projects)
            for line in csv_reader:
                if line[0] == value:
                    raise ValidationError('This Slate Project directory name already exists')
