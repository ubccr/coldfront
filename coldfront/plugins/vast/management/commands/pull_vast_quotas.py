import logging

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, AllocationAttribute, AllocationAttributeType
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.config.plugins.vast import VASTAUTHORIZER
from coldfront.plugins.vast.utils import client

if VASTAUTHORIZER == 'AD':
    from coldfront.plugins.ldap.utils import LDAPConn

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Pull VAST quotas and update the database"

    def handle(self, *args, **options):
        """
        Pull VAST quotas and update the database.
        """
        resource_name = 'holylabs'
        quotas = client.userquotas.get(
            # entity__identifier_type="gid",
            entity__is_group=True,
            path__startswith=f'/{resource_name}'
        )
        # translate gids to AD group names via the ldap plugin
        ad = LDAPConn()
        vast_resource = Resource.objects.get(name=f'vast-{resource_name}')
        quota_bytes_aa_type = AllocationAttributeType.objects.get(name='Quota_In_Bytes')
        quota_tib_aa_type = AllocationAttributeType.objects.get(name='Storage Quota (TiB)')
        path_aa_type = AllocationAttributeType.objects.get(name='Subdirectory')
        group_names = []
        for quota_dict in quotas['results']:
            if VASTAUTHORIZER == 'AD':
                if quota_dict['entity']['identifier_type'] == 'gid':
                    gid = quota_dict['entity']['identifier']
                    group_result = ad.search_groups({'gidNumber': gid}, attributes=['sAMAccountName'])
                    if group_result:
                        group_name = group_result[0]['sAMAccountName'][0]
                    else:
                        logger.error("could not find matching AD group for quota_dict %s", quota_dict)
                        print(f"could not find matching AD group for quota_dict {quota_dict}")
                        continue
                elif quota_dict['entity']['identifier_type'] == 'groupname':
                    group_name = quota_dict['entity']['identifier']
                else:
                    print(f"Unhandled identifier type: {quota_dict['entity']['identifier_type']}")
                    continue
                quota_dict['entity']['name'] = group_name
                group_names.append(group_name)
                quota_bytes = quota_dict['hard_limit']
                usage_bytes = quota_dict['used_capacity']
                try:
                    allocation = Allocation.objects.get(
                        project=Project.objects.get(title=quota_dict['entity']['name']),
                        resources=vast_resource
                    )
                except Allocation.DoesNotExist:
                    allocation = Allocation.objects.create(
                        project=Project.objects.get(title=quota_dict['entity']['name']),
                        status=AllocationStatusChoice.objects.get(name="Active")
                    )
                    allocation.resources.add(vast_resource)
                    logger.info("Created new allocation for project %s", quota_dict['entity']['name'])
                except Project.DoesNotExist:
                    print(f"Project {quota_dict['entity']['name']} does not exist.")
                    logger.error("Project %s does not exist.", quota_dict['entity']['name'])
                    continue
                quota_bytes_attr, created = AllocationAttribute.objects.update_or_create(
                    allocation=allocation,
                    allocation_attribute_type=quota_bytes_aa_type,
                    defaults={'value': quota_bytes}
                )
                quota_bytes_attr.allocationattributeusage.value = usage_bytes
                quota_bytes_attr.allocationattributeusage.save()
                quota_tib = quota_bytes / 1024 / 1024 / 1024 / 1024
                quota_tib_attr, created = AllocationAttribute.objects.update_or_create(
                    allocation=allocation,
                    allocation_attribute_type=quota_tib_aa_type,
                    defaults={'value': quota_tib}
                )
                if usage_bytes > 1000:
                    usage_tib = usage_bytes / 1024 / 1024 / 1024 / 1024
                else:
                    usage_tib = 0
                quota_tib_attr.allocationattributeusage.value = usage_tib
                quota_tib_attr.allocationattributeusage.save()
                if not allocation.path:
                    AllocationAttribute.objects.get_or_create(
                            allocation=allocation,
                            allocation_attribute_type=path_aa_type,
                            defaults={'value': f'C/{allocation.project.title}'},
                    )
        # check for active vast-resource coldfront allocations that haven't been updated
        allocations = Allocation.objects.filter(
                resources=vast_resource,
                status__name="Active"
        )
        for allocation in allocations:
            if allocation.project.title not in group_names:
                logger.warning("Allocation %s for project %s is not in VAST quotas, deactivating",
                               allocation.id, allocation.project.title)
                allocation.status = AllocationStatusChoice.objects.get(name="Inactive")
                allocation.save()
                print(f"Allocation {allocation.id} for project {allocation.project.title} is not in VAST quotas, removing")
