from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import ResourceType
from coldfront.core.allocation.models import AllocationAttributeType, \
    SecureDirAddUserRequestStatusChoice, SecureDirRemoveUserRequestStatusChoice

from django.core.management.base import BaseCommand

import os
import logging

"""An admin command that creates Resource-related objects for storing 
relevant cluster directories."""


class Command(BaseCommand):
    help = 'Manually creates objects for storing relevant cluster directories.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """
        Creates default objects used for storing cluster directories
        """
        from coldfront.core.resource.models import AttributeType
        attribute_type, _ = AttributeType.objects.get_or_create(name='Text')
        path, _ = ResourceAttributeType.objects.update_or_create(
            attribute_type=AttributeType.objects.get(name='Text'),
            name='path',
            defaults={
                'is_required': True,
                'is_unique_per_resource': True,
                'is_value_unique': True,
            })

        cluster_directory, _ = ResourceType.objects.update_or_create(
            name='Cluster Directory',
            defaults={
                'description': 'Directory on a cluster.',
            })

        groups_directory, _ = Resource.objects.update_or_create(
            resource_type=cluster_directory,
            name='Groups Directory',
            description='The parent directory containing shared group data.')

        groups_path, _ = ResourceAttribute.objects.update_or_create(
            resource_attribute_type=path,
            resource=groups_directory,
            value='/global/home/groups/')

        scratch2_directory, _ = Resource.objects.update_or_create(
            resource_type=cluster_directory,
            name='Scratch2 Directory',
            description='The parent directory containing scratch2 data.')

        scratch2_path, _ = ResourceAttribute.objects.update_or_create(
            resource_attribute_type=path,
            resource=scratch2_directory,
            value='/global/scratch2/')

        groups_pl1_directory, _ = Resource.objects.update_or_create(
            parent_resource=groups_directory,
            resource_type=cluster_directory,
            name='Groups PL1 Directory',
            description='The parent directory containing PL1 data '
                        'in the groups directory.')

        groups_pl1_path, _ = ResourceAttribute.objects.update_or_create(
            resource_attribute_type=path,
            resource=groups_pl1_directory,
            value=os.path.join(groups_path.value, 'pl1data'))

        scratch2_pl1_directory, _ = Resource.objects.update_or_create(
            parent_resource=scratch2_directory,
            resource_type=cluster_directory,
            name='Scratch2 PL1 Directory',
            description='The parent directory containing PL1 data in the '
                        'scratch2 directory.')

        scratch2_pl1_path, _ = ResourceAttribute.objects.update_or_create(
            resource_attribute_type=path,
            resource=scratch2_pl1_directory,
            value=os.path.join(scratch2_path.value, 'pl1data'))

        from coldfront.core.allocation.models import AttributeType
        attribute_type, _ = AttributeType.objects.get_or_create(name='Text')
        allocation_attr_type, _ = \
            AllocationAttributeType.objects.update_or_create(
                attribute_type=attribute_type,
                name='Cluster Directory Access',
                defaults={
                    'has_usage': False,
                    'is_required': False,
                    'is_unique': False,
                    'is_private': False,
                })

        for status in ['Pending - Add', 'Processing - Add', 'Completed', 'Denied']:
            SecureDirAddUserRequestStatusChoice.objects.get_or_create(
                name=status)

        for status in ['Pending - Remove', 'Processing - Remove', 'Completed', 'Denied']:
            SecureDirRemoveUserRequestStatusChoice.objects.get_or_create(
                name=status)

        message = 'Successfully created directory objects.'
        self.stdout.write(self.style.SUCCESS(message))
