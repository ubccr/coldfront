import logging

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation
from coldfront.core.projects.models import Project
from coldfront.core.resources.models import Resource
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
        for quota_dict in quotas['results']:
            if VASTAUTHORIZER == 'AD':
                if quota_dict['entity']['identifier_type'] == 'gid':
                    gid = quota_dict['entity']['identifier']
                    group_name = ad.search_groups({'gidNumber': gid}, attributes=['sAMAccountName'])
                    if group_name:
                        quota_dict['entity']['name'] = group_name
                        quota_dict.entity.save()
                elif quota_dict['entity']['identifier_type'] == 'groupname':
                    quota_dict['entity']['name'] = quota_dict['entity']['identifier']
                else:
                    print(f"Unhandled identifier type: {quota_dict['entity']['identifier_type']}")
                    continue
                quota_bytes = quota_dict['hard_limit']
                usage_bytes = quota_dict['used_capacity']
                try:
                    allocation = Allocation.objects.get(
                        project=Project.objects.get(title=quota_dict['entity']['name']),
                        resources__name=''
                    )
                except Allocation.DoesNotExist:
                    allocation = Allocation.objects.create(
                        project=Project.objects.get(title=quota_dict['entity']['name']),
                    )
                    allocation.resources.add(vast_resource)
                    logger.info("Created new allocation for project %s", quota_dict['entity']['name'])
                except Project.DoesNotExist:
                    print(f"Project {quota_dict['entity']['name']} does not exist.")
                    logger.error("Project %s does not exist.", quota_dict['entity']['name'])
                    continue

                allocation.update(
                        bytes=quota_bytes,
                        used= usage_bytes,
                )



