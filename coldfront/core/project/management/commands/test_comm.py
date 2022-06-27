import os

from django.core.management.base import BaseCommand
from coldfront.core.project.models import *
from coldfront.core.allocation.models import *

class Command(BaseCommand):

    def handle(self, *args, **options):
        project = Project.objects.get(name='fc_dynein')
        proj_user = project.projectuser_set.get(user__username='jofeinstein')
        user_obj = proj_user.user

        allocation = Allocation.objects.get(project=project)
        allocation_user = allocation.allocationuser_set.get(user=user_obj)

        # should be 'Removed' after removal
        print(allocation_user.status)

        cluster_account_status = \
            allocation_user.allocationuserattribute_set.get(
                allocation_attribute_type=AllocationAttributeType.objects.get(
                    name='Cluster Account Status'))

        # should be 'Denied'
        print(cluster_account_status.value)

        print(proj_user.status.name)

        allocation_user_status_choice_removed = \
            AllocationUserStatusChoice.objects.get(name='Removed')

        print(allocation.allocationuser_set.exclude(status=allocation_user_status_choice_removed))
        print(allocation.allocationuser_set.filter(status=allocation_user_status_choice_removed))