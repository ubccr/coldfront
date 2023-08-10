import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.resource.models import AttributeType
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import ResourceType
from coldfront.core.resource.models import TimedResourceAttribute
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances

"""An admin command that creates database objects related to computing
allowances."""


class Command(BaseCommand):

    help = 'Creates database objects related to computing allowances.'

    def handle(self, *args, **options):
        self.create_resource_types()
        self.create_resource_attribute_types()
        data = self.get_allowance_resource_and_attribute_data()
        self.create_allowance_resources_and_attributes(data)

    def create_allowance_resources_and_attributes(self, data):
        """Given a list of dicts representing computing allowance
        Resources and their attributes, create Resource and
        ResourceAttribute objects."""
        for allowance in data:
            resource, _ = Resource.objects.update_or_create(
                resource_type=self.computing_allowance,
                name=allowance['name'],
                defaults={
                    'description': allowance['description'],
                })
            for resource_attribute_type, value in allowance['attributes']:
                ResourceAttribute.objects.update_or_create(
                    resource_attribute_type=resource_attribute_type,
                    resource=resource,
                    defaults={
                        'value': value,
                    })
            for resource_attribute_type, start_date, end_date, value in \
                    allowance.get('timed_attributes', []):
                TimedResourceAttribute.objects.update_or_create(
                    resource_attribute_type=resource_attribute_type,
                    resource=resource,
                    start_date=start_date,
                    end_date=end_date,
                    defaults={
                        'value': value,
                    })

    def create_resource_attribute_types(self):
        """Create ResourceAttributeTypes for attributes of computing
        allowance Resources. Set instance attributes to them."""
        decimal, _ = AttributeType.objects.update_or_create(name='Decimal')
        text = AttributeType.objects.get(name='Text')

        self.service_units, _ = ResourceAttributeType.objects.update_or_create(
            attribute_type=decimal,
            name='Service Units',
            defaults={
                'is_required': False,
                'is_unique_per_resource': True,
                'is_value_unique': False,
            })
        self.name_long, _ = ResourceAttributeType.objects.update_or_create(
            attribute_type=text,
            name='name_long',
            defaults={
                'is_required': False,
                'is_unique_per_resource': True,
                'is_value_unique': True,
            })
        self.name_short, _ = ResourceAttributeType.objects.update_or_create(
            attribute_type=text,
            name='name_short',
            defaults={
                'is_required': False,
                'is_unique_per_resource': True,
                'is_value_unique': True,
            })
        self.code, _ = ResourceAttributeType.objects.update_or_create(
            attribute_type=text,
            name='code',
            defaults={
                'is_required': False,
                'is_unique_per_resource': True,
                'is_value_unique': True,
            })

    def create_resource_types(self):
        """Create a ResourceType for computing allowances. Set an instance
        attribute to it."""
        self.computing_allowance, _ = ResourceType.objects.update_or_create(
            name='Computing Allowance',
            defaults={
                'description': 'An allowance of compute time on a cluster.',
            })

    def get_allowance_resource_and_attribute_data(self):
        """Return a list of dicts representing computing allowance
        Resources and their attributes."""
        # Allowances are based on flags.
        data_by_flag_name = {
            'BRC_ONLY': [
                {
                    'name': BRCAllowances.FCA,
                    'description': (
                        'A free computing allowance available to faculty.'),
                    'attributes': [
                        (self.name_long, 'Faculty Computing Allowance (FCA)'),
                        (self.name_short, 'FCA'),
                        (self.code, 'fc_'),
                    ],
                },
                {
                    'name': BRCAllowances.CO,
                    'description': (
                        'A computing allowance available to Condo partners.'),
                    'attributes': [
                        (self.service_units, f'{settings.ALLOCATION_MAX}'),
                        (self.name_long, 'Condo Allocation'),
                        (self.name_short, 'CO'),
                        (self.code, 'co_'),
                    ],
                },
                {
                    'name': BRCAllowances.RECHARGE,
                    'description': 'A paid computing allowance.',
                    'attributes': [
                        (self.name_long, 'Recharge Allocation (Buy Time)'),
                        (self.name_short, 'RECHARGE'),
                        (self.code, 'ac_'),
                    ],
                },
                {
                    'name': BRCAllowances.ICA,
                    'description': (
                        'A free computing allowance available to '
                        'instructors.'),
                    'attributes': [
                        (self.name_long,
                         'Instructional Computing Allowance (ICA)'),
                        (self.name_short, 'ICA'),
                        (self.code, 'ic_'),
                    ],
                },
                {
                    'name': BRCAllowances.PCA,
                    'description': (
                        'A free computing allowance available in special '
                        'cases.'),
                    'attributes': [
                        (self.name_long, 'Partner Computing Allowance (PCA)'),
                        (self.name_short, 'PCA'),
                        (self.code, 'pc_'),
                    ],
                },
            ],
            'LRC_ONLY': [
                {
                    'name': LRCAllowances.PCA,
                    'description': (
                        'A free computing allowance available to PIs.'),
                    'attributes': [
                        (self.name_long, 'PI Computing Allowance (PCA)'),
                        (self.name_short, 'PCA'),
                        (self.code, 'pc_'),
                    ],
                },
                {
                    'name': LRCAllowances.LR,
                    'description': (
                        'A computing allowance available to Condo partners.'),
                    'attributes': [
                        (self.service_units, f'{settings.ALLOCATION_MAX}'),
                        (self.name_long, 'Condo Allocation'),
                        (self.name_short, 'LR'),
                        (self.code, 'lr_'),
                    ],
                },
                {
                    'name': LRCAllowances.RECHARGE,
                    'description': 'A paid computing allowance.',
                    'attributes': [
                        (self.service_units, f'{settings.ALLOCATION_MAX}'),
                        (self.name_long,
                            'Recharge Allocation (Pay for Used Time)'),
                        (self.name_short, 'RECHARGE'),
                        (self.code, 'ac_'),
                    ],
                },
            ],
        }

        service_units_files_by_flag_name = {
            'BRC_ONLY': 'data/brc_service_units.json',
            'LRC_ONLY': 'data/lrc_service_units.json',
        }

        data = []
        for flag_name, allowances in data_by_flag_name.items():
            if flag_enabled(flag_name):
                service_units_file_path = os.path.join(
                    os.path.dirname(__file__),
                    service_units_files_by_flag_name[flag_name])
                with open(service_units_file_path, 'r') as f:
                    # A mapping from allowance name to a list of objects
                    # specifying how many Service Units the allowance grants
                    # during a particular AllocationPeriod.
                    service_units_data = json.load(f)
                for allowance in allowances:
                    if allowance['name'] in service_units_data:
                        allowance['timed_attributes'] = []
                        for allocation_period_value in service_units_data[
                                allowance['name']]:
                            allocation_period = AllocationPeriod.objects.get(
                                name=allocation_period_value[
                                    'allocation_period'])
                            value = allocation_period_value['value']
                            allowance['timed_attributes'].append(
                                (
                                    self.service_units,
                                    allocation_period.start_date,
                                    allocation_period.end_date,
                                    value,
                                )
                            )
                data.extend(allowances)
        return data
