import logging
import os
import tempfile

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from coldfront.core.project.models import Project
from coldfront.core.allocation.models import (
    AllocationStatusChoice,
    AllocationAttributeType,
    AllocationUserAttributeType,
    AllocationUserStatusChoice,
)
from coldfront.core.resource.models import Resource
from coldfront.plugins.slurm.utils import SlurmError, slurm_dump_cluster
from coldfront.plugins.slurm.associations import SlurmCluster

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import all Slurm allocations into Coldfront.'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file',
            help='designate a file with sacctmgr dump data to use as a datasource')

    def _cluster_from_dump(self, cluster, file=None):
        slurm_cluster = None
        if file:
            with open(file) as data:
                slurm_cluster = SlurmCluster.new_from_stream(data)
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                fname = os.path.join(tmpdir, 'cluster.cfg')
                cluster_name = cluster.get_attribute("slurm_cluster")
                try:
                    slurm_dump_cluster(cluster_name, fname)
                    with open(fname) as fh:
                        slurm_cluster = SlurmCluster.new_from_stream(fh)
                except SlurmError as e:
                    logger.error('Failed to dump Slurm cluster %s: %s', cluster, e)
        slurm_cluster.pull_fairshares()
        return slurm_cluster

    def handle(self, *args, **options):
        # make new SlurmCluster obj containing the dump from the cluster
        file = options['file']
        cluster_resources = Resource.objects.filter(
            resource_type__name='Cluster', is_available=True
        )
        slurm_clusters = {r: self._cluster_from_dump(r, file=file) for r in cluster_resources}
        slurm_clusters = {
            r:c for r, c in slurm_clusters.items() if r.get_attribute('slurm_cluster') == c.name
        }

        slurm_acct_name_attr_type_obj = AllocationAttributeType.objects.get(
            name='slurm_account_name')
        cloud_acct_name_attr_type_obj = AllocationAttributeType.objects.get(
            name='Cloud Account Name')
        hours_attr_type_obj = AllocationAttributeType.objects.get(
            name='Core Usage (Hours)')
        auser_status_active = AllocationUserStatusChoice.objects.get(name='Active')

        for resource, cluster in slurm_clusters.items():

            # create an allocation for each account
            undetected_projs = []
            for name, account in cluster.accounts.items():
                try:
                    project_obj = Project.objects.get(title=name)
                except Project.DoesNotExist:
                    print(f'no project with title {name} detected.')
                    undetected_projs.append(name)
                    continue

                allocation_objs = project_obj.allocation_set.filter(
                    resources__name=resource.name,
                )
                if not allocation_objs:
                    allocation_obj = project_obj.allocation_set.create(
                        status=AllocationStatusChoice.objects.get(name='Active'),
                        start_date=timezone.now()
                    )
                    allocation_obj.resources.add(resource)
                    allocation_obj.save()
                elif len(allocation_objs) == 1:
                    allocation_obj = allocation_objs.first()
                elif len(allocation_objs) > 1:
                    print('Too many allocations:', allocation_objs)
                    logger.warning(
                        'multiple allocations returned for project %s resource %s',
                        project_obj.title, resource.name
                    )
                    continue
                # used in XDMOD to correspond with pi_filter, I think
                # 'slurm_account_name'? XDMOD_ACCOUNT_ATTRIBUTE_NAME

                allocation_obj.allocationattribute_set.get_or_create(
                    allocation_attribute_type=slurm_acct_name_attr_type_obj,
                    value=name)
                # add allocation_obj attrs:
                # 'Cloud Account Name'? XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME
                allocation_obj.allocationattribute_set.get_or_create(
                    allocation_attribute_type=cloud_acct_name_attr_type_obj,
                    value=name
                )

                allocation_obj.allocationattribute_set.get_or_create(
                    allocation_attribute_type=hours_attr_type_obj,
                    defaults={'value': 0}
                )

                for shareval in ['FairShare', 'NormShares', 'RawUsage', 'EffectvUsage']:
                    try:
                        group_val = account.fairshare_dict.get(shareval, None)
                    except AttributeError:
                        group_val = None

                    if group_val:
                        attr_type = AllocationAttributeType.objects.get(name=shareval)
                        allocation_obj.allocationattribute_set.update_or_create(
                            allocation_attribute_type=attr_type,
                            defaults={'value': group_val}
                        )

                # add allocationusers from account
                for user_name, user_account in account.users.items():
                    try:
                        user = get_user_model().objects.get(username=user_name)
                    except Exception:
                        print('no user found:', user_name)
                        continue
                    alloc_user, _ = allocation_obj.allocationuser_set.get_or_create(
                        user=user,
                        defaults={
                            'status': auser_status_active, 'unit': 'CPU Hours'
                        }
                    )

                    for shareval in ['FairShare', 'NormShares', 'RawUsage', 'EffectvUsage']:
                        try:
                            user_val = user_account.fairshare_dict.get(shareval, None)
                        except AttributeError:
                            user_val = None
                        if user_val:
                            attr_type = AllocationUserAttributeType.objects.get(name=shareval)
                            alloc_user.allocationuserattribute_set.update_or_create(
                                allocationuser_attribute_type=attr_type,
                                defaults={'value': user_val}
                            )
            if undetected_projs:
                logger.warning(
                    '%s Accounts without corresponding projects detected: %s',
                    resource, undetected_projs
                )
