from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import ResourceType
from coldfront.core.allocation.models import AllocationAttributeType, \
    SecureDirAddUserRequestStatusChoice, SecureDirRemoveUserRequestStatusChoice, \
    SecureDirRequestStatusChoice

from django.core.management.base import BaseCommand

import os
import logging

"""An admin command that creates objects for storing 
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
        path, _ = ResourceAttributeType.objects.get_or_create(
            attribute_type=AttributeType.objects.get(name='Text'),
            name='path',
            defaults={
                'is_required': True,
                'is_unique_per_resource': True,
                'is_value_unique': True,
            })

        cluster_directory, _ = ResourceType.objects.get_or_create(
            name='Cluster Directory',
            defaults={
                'description': 'Directory on a cluster.',
            })

        groups_directory, _ = Resource.objects.get_or_create(
            resource_type=cluster_directory,
            name='Groups Directory',
            description='The parent directory containing shared group data.')

        groups_path, _ = ResourceAttribute.objects.get_or_create(
            resource_attribute_type=path,
            resource=groups_directory,
            value='/global/home/groups/')

        scratch_directory, _ = Resource.objects.get_or_create(
            resource_type=cluster_directory,
            name='Scratch Directory',
            description='The parent directory containing scratch data.')

        scratch_path, _ = ResourceAttribute.objects.get_or_create(
            resource_attribute_type=path,
            resource=scratch_directory,
            value='/global/scratch/')

        groups_p2p3_directory, _ = Resource.objects.get_or_create(
            parent_resource=groups_directory,
            resource_type=cluster_directory,
            name='Groups P2/P3 Directory',
            description='The parent directory containing P2/P3 data '
                        'in the groups directory.')

        groups_p2p3_path, _ = ResourceAttribute.objects.get_or_create(
            resource_attribute_type=path,
            resource=groups_p2p3_directory,
            value=os.path.join(groups_path.value, 'pl1data'))

        scratch_p2p3_directory, _ = Resource.objects.get_or_create(
            parent_resource=scratch_directory,
            resource_type=cluster_directory,
            name='Scratch P2/P3 Directory',
            description='The parent directory containing P2/P3 data in the '
                        'scratch directory.')

        scratch_p2p3_path, _ = ResourceAttribute.objects.get_or_create(
            resource_attribute_type=path,
            resource=scratch_p2p3_directory,
            value=os.path.join(scratch_path.value, 'p2p3'))

        from coldfront.core.allocation.models import AttributeType
        attribute_type, _ = AttributeType.objects.get_or_create(name='Text')
        allocation_attr_type, _ = \
            AllocationAttributeType.objects.get_or_create(
                attribute_type=attribute_type,
                name='Cluster Directory Access',
                defaults={
                    'has_usage': False,
                    'is_required': False,
                    'is_unique': False,
                    'is_private': False,
                })

        for status in ['Pending',
                       'Processing',
                       'Complete',
                       'Denied']:
            SecureDirAddUserRequestStatusChoice.objects.get_or_create(
                name=status)
            SecureDirRemoveUserRequestStatusChoice.objects.get_or_create(
                name=status)

        choices = [
            'Approved - Complete',
            'Approved - Processing',
            'Denied',
            'Under Review',
        ]
        for choice in choices:
            SecureDirRequestStatusChoice.objects.get_or_create(name=choice)
