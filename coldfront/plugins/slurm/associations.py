import datetime
import logging
import os
import re
import sys

from coldfront.core.allocation.models import (
        Allocation,
        AllocationStatusChoice,
        AllocationAttribute,
        AllocationAttributeType,
)
from coldfront.core.project.models import Project
from coldfront.core.resource.models import (
        Resource,
        ResourceType,
        ResourceAttribute,
        ResourceAttributeType,
)
from coldfront.plugins.slurm.utils import (
    SLURM_ACCOUNT_ATTRIBUTE_NAME,
    SLURM_CLUSTER_ATTRIBUTE_NAME,
    SLURM_SPECS_ATTRIBUTE_NAME,
    SLURM_USER_SPECS_ATTRIBUTE_NAME,
    slurm_collect_shares,
    slurm_collect_usage,
    slurm_list_partitions,
    slurm_fixed_width_lines_to_dict,
    SlurmError,
)


logger = logging.getLogger(__name__)


class SlurmParserError(SlurmError):
    pass


class SlurmBase:
    def __init__(self, name, specs=None):
        if specs is None:
            specs = []

        self.name = name
        self.specs = specs

    def spec_list(self):
        """Return unique list of Slurm Specs"""
        items = []
        for s in self.specs:
            for i in s.split(':'):
                items.append(i)

        return list(set(items))

    def spec_dict(self):
        """Return dict of Slurm Specs"""
        spec_dict = {}
        for s in self.specs:
            i = s.split('=')
            spec_dict[i[0]] = i[1]
        return spec_dict

    def format_specs(self):
        """Format unique list of Slurm Specs"""
        return ':'.join(self.spec_list())

    def format_share(self):
        if hasattr(self, 'share_dict'):
            return ', '.join(f"{key}:{value}" for key, value in self.share_dict.items())
        return ""

    def _write(self, out, data):
        try:
            out.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)


class SlurmCluster(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.accounts = {}

    @staticmethod
    def new_from_stream(stream):
        """Create a new SlurmCluster by parsing the output from sacctmgr dump."""
        cluster = None
        parent = None
        name = ""
        for line in stream:
            line = line.strip()
            if re.match("^#", line):
                continue
            if re.match("^Cluster - '[^']+'", line):
                parts = line.split(':')
                name = re.sub(r"^Cluster - ", '', parts[0]).strip("\n'")
                if len(name) == 0:
                    raise SlurmParserError(f'Cluster name not found for line: {line}')
                cluster = SlurmCluster(name)
                cluster.specs += parts[1:]
            elif re.match("^Account - '[^']+'", line):
                account = SlurmAccount.new_from_sacctmgr(line)
                cluster.accounts[account.name] = account
            elif re.match("^Parent - '[^']+'", line):
                parent = re.sub(r"^Parent - ", '', line).strip("\n'")
                if parent == 'root':
                    cluster.accounts['root'] = SlurmAccount('root')
                if not parent:
                    raise SlurmParserError(
                        f'Parent name not found for line: {line}')
            elif re.match("^User - '[^']+'", line):
                user = SlurmUser.new_from_sacctmgr(line)
                if not parent:
                    raise SlurmParserError(
                        f'Found user record without Parent for line: {line}')
                account = cluster.accounts[parent]
                account.add_user(user)
                cluster.accounts[parent] = account

        if not cluster or not cluster.name:
            raise SlurmParserError(
                'Failed to parse Slurm cluster name. Is this in sacctmgr dump file format?')
        logger.debug(f"\x1b[33;20m  Cluster '{name}' accounts and users loaded \x1b[0m")
        return cluster

    @staticmethod
    def new_from_resource(resource):
        """Create a new SlurmCluster from a ColdFront Resource model."""
        name = resource.get_attribute(SLURM_CLUSTER_ATTRIBUTE_NAME)
        specs = resource.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
        user_specs = resource.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        if not name:
            raise SlurmError(f'Resource {resource} missing slurm_cluster')

        cluster = SlurmCluster(name, specs)

        # Process allocations
        for allocation in resource.allocation_set.filter(
            status__name__in=['Active', 'Renewal Requested']
        ):
            cluster.add_allocation(allocation, user_specs=user_specs)

        # Process child resources
        children = Resource.objects.filter(
            parent_resource_id=resource.id, resource_type__name='Cluster Partition')
        for r in children:
            partition_specs = r.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
            partition_user_specs = r.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
            for allocation in r.allocation_set.filter(
                status__name__in=['Active', 'Renewal Requested']
            ):
                cluster.add_allocation(
                    allocation, specs=partition_specs, user_specs=partition_user_specs
                )

        return cluster

    def add_allocation(self, allocation, specs=None, user_specs=None):
        """Add accounts from a ColdFront Allocation model to SlurmCluster"""
        if specs is None:
            specs = []

        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = 'root'

        logger.info(f"Adding allocation name={name} specs={specs} user_specs={user_specs}")
        account = self.accounts.get(name, SlurmAccount(name))
        account.add_allocation(allocation, user_specs=user_specs)
        account.specs += specs
        self.accounts[name] = account

    def id_partition_projects(self, partition_info):
        """identify the partition projects
        Crossreference Allow/DenyAccounts and Allow/DenyGroups.
        Projects must be permitted on both lists to access a given partition.
        """
        # identify allowed_groups
        all_slurm_account_names = [a.name for a in list(self.accounts.values())]
        allowed_groups = partition_info.get('AllowGroups', '').split(',')
        denied_accounts = partition_info.get('DenyAccounts', '').split(',')
        # if 'cluster_users' is in allowed_groups, then all users/accounts are allowed
        if 'cluster_users' in allowed_groups:
            partition_project_names = [a for a in all_slurm_account_names if a not in denied_accounts]
        else:
            allowed_accounts = partition_info.get('AllowAccounts', 'NA').split(',')
            if allowed_accounts == ['ALL']:
                partition_project_names = allowed_groups
            elif allowed_accounts == ['NA']:
                partition_project_names = [a for a in allowed_groups if a not in denied_accounts]
            else:
                partition_project_names = set(allowed_groups + allowed_accounts)

        return partition_project_names

    def append_partitions(self):
        """append partition data to accounts"""

        def create_allocation_attributes(project, justification, quantity, resource):
            new_allocation = Allocation.objects.create(
                project=project, justification=justification, quantity=quantity,
                status=AllocationStatusChoice.objects.get(name="Active"),
            )
            new_allocation.resources.add(resource)
            attribute_name_type = AllocationAttributeType.objects.get(name=SLURM_ACCOUNT_ATTRIBUTE_NAME)
            AllocationAttribute.objects.create(
                allocation=new_allocation,
                allocation_attribute_type_id=attribute_name_type.pk,
                value=project.title
            )
            slurm_specs_attribute_type = AllocationAttributeType.objects.get(name=SLURM_SPECS_ATTRIBUTE_NAME)
            slurm_spec_list =  ['EffectvUsage', 'RawUsage', 'Fairshare', 'NormShare', 'RawShare']
            attribute_value = ""
            for slurm_spec in slurm_spec_list:
                # TODO get Shares values for Allocation
                attribute_value += f'{slurm_spec}=0,'
            attribute_value = attribute_value.rstrip(',')
            AllocationAttribute.objects.create(
                allocation=new_allocation,
                allocation_attribute_type_id=slurm_specs_attribute_type.pk,
                value=attribute_value
            )
            return new_allocation

        partitions = slurm_list_partitions()
        current_cluster_resource = Resource.objects.filter(
            resourceattribute__value=self.name, resource_type__name='Cluster').first()
        if not current_cluster_resource:
            logger.debug("Current cluster resource not found", True)
            return
        partition_resourcetype = ResourceType.objects.get(name='Cluster Partition')
        slurm_specs_resourceattribute_type = ResourceAttributeType.objects.get(name=SLURM_SPECS_ATTRIBUTE_NAME)
        for partition in partitions:
            partition_resource, created = Resource.objects.get_or_create(
                name=partition['PartitionName'],
                parent_resource=current_cluster_resource,
                resource_type=partition_resourcetype,
            )
            partition_resource.resourceattribute_set.update_or_create(
                resource_attribute_type=slurm_specs_resourceattribute_type,
                defaults={'value': partition['TRESBillingWeights']}
            )
            partition_project_names = self.id_partition_projects(partition)
            # Retrieve all projects that have the same name as the resource accounts
            matching_projects = Project.objects.filter(title__in=partition_project_names)
            # look for allocations belonging to projects outside of the
            # partition_project_names that have this resource
            matching_allocations = Allocation.objects.filter(resources=partition_resource)
            for allocation in matching_allocations:
                if allocation.project not in matching_projects:
                    allocation.resources.remove(partition_resource)

            allocations_missing_partition = Allocation.objects.filter(
                    project__in=matching_projects, resources=current_cluster_resource
            ).exclude(resources=partition_resource)
            for allocation in allocations_missing_partition:
                allocation.resources.add(partition_resource)

            projects_without_allocations = matching_projects.exclude(
                allocation__resources=partition_resource
            )
            logger.info(f'projects without cluster allocations that are on a partition access list: {projects_without_allocations}')
            # for project in projects_without_allocations:
            #     new_allocation = create_allocation_attributes(
            #             project, 'slurm_sync', 1, current_cluster_resource
            #     )
            #     new_allocation.resources.add(partition_resource)
            #     new_allocation.save()
            #     self.add_allocation(new_allocation)

    def pull_sshare_data(self, file=None):
        """append sshare data to accounts and users"""
        def map_shares(share_info):
            return {
                'RawShares': share_info['RawShares'] or 0, 'NormShares': share_info['NormShares'] or 0,
                'RawUsage': share_info['RawUsage'] or 0, 'FairShare': share_info['FairShare'] or 0
            }

        if not file:
            share_info = slurm_collect_shares(cluster=self.name)
        else:
            with open(file, 'r') as share_file:
                share_data = list(share_file)
                share_info = slurm_fixed_width_lines_to_dict(share_data)
        # select all share lines with no user val, pin to SlurmAccounts.
        accounts_share = [share for share in share_info if not share['User']]
        # pair accounts_share with SlurmAccounts
        for acct_share in accounts_share:
            account = next(
                (a for a in self.accounts.values() if a.name == acct_share['Account']), None
            )
            if not account:
                logger.debug(f" No account for {acct_share}")
                continue
            user_shares = [
                d for d in share_info if d['Account'] == acct_share['Account'] and d['User']
            ]
            for user_share in user_shares:
                user = next((u for u in account.users.values() if u.name == user_share['User']), None)
                if not user:
                    logger.debug(f" No user for {user_share}")
                    continue
                if not hasattr(user, 'share_dict'):
                    user.share_dict = map_shares(user_share)
                else:
                    print("OVERWRITE BLOCKED:", user, user.share_dict, user_share)
            if not hasattr(account, 'share_dict'):
                account.share_dict = map_shares(acct_share)
            else:
                print("OVERWRITE BLOCKED:", account, account.share_dict, acct_share)
        logger.debug(f"\x1b[33;20m  Cluster '{self.name}' accounts and users share Info loaded \x1b[0m")

    def pull_usage(self):
        """append sreport usage data to accounts and users"""
        usages = slurm_collect_usage(cluster=self.name)
        acct_usages = [d for d in usages if not d['Login']]
        for acct_usage in acct_usages:
            account = next((a for a in self.accounts.values() if a.name == acct_usage['Account']), None)
            if not account:
                print(f"no account for {acct_usage}")
                continue
            user_usages = [d for d in usages if d['Account'] == account.name and d['Login']]
            for user_usage in user_usages:
                user = next((u for u in account.users.values() if u.name == user_usage['Login']), None)
                if not user:
                    print(f"no user for {user_usage}")
                    continue
                if not hasattr(user, 'usage_dict'):
                    user.usage_dict = user_usage
                else:
                    print("OVERWRITE BLOCKED:", user, user.usage_dict, user_usage)
            if not hasattr(account, 'usage_dict'):
                account.usage_dict = acct_usage
            else:
                print("OVERWRITE BLOCKED:", account, account.usage_dict, acct_usage)

    def write(self, out):
        self._write(
            out,
            f"# ColdFront Allocation Slurm associations dump {datetime.datetime.now().date()}\n"
        )
        self._write(out, f"Cluster - '{self.name}':{self.format_specs()}\n")
        if 'root' in self.accounts:
            self.accounts['root'].write(out)
        else:
            self._write(out, "Parent - 'root'\n")
            self._write(
                out, "User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1\n"
            )

        for account in self.accounts.values():
            if account.name == 'root':
                continue
            account.write_users(out)


class SlurmAccount(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.users = {}

    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmAccount by parsing a line from sacctmgr dump. For
        example: Account - 'physics':Description='physics group':Organization='cas':Fairshare=100"""
        if not re.match("^Account - '[^']+'", line):
            raise SlurmParserError(
                f'Invalid format. Must start with "Account" for line: {line}')

        parts = line.split(':')
        name = re.sub(r"^Account - ", '', parts[0]).strip("\n'")
        if len(name) == 0:
            raise SlurmParserError(f'Cluster name not found for line: {line}')

        return SlurmAccount(name, specs=parts[1:])

    def add_allocation(self, allocation, user_specs=None):
        """Add users from a ColdFront Allocation model to SlurmAccount"""
        if user_specs is None:
            user_specs = []

        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = 'root'

        if name != self.name:
            raise SlurmError(
                f'Allocation {allocation} slurm_account_name does not match {self.name}')

        self.specs += allocation.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)

        allocation_user_specs = allocation.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        for u in allocation.allocationuser_set.filter(status__name='Active'):
            user = SlurmUser(u.user.username)
            user.specs += allocation_user_specs
            user.specs += user_specs
            self.add_user(user)

    def add_user(self, user):
        if user.name not in self.users:
            self.users[user.name] = user

        rec = self.users[user.name]
        rec.specs += user.specs
        self.users[user.name] = rec

    def write(self, out):
        if self.name != 'root':
            self._write(out, f"Account - '{self.name}': Specs {self.format_specs()} - Share {self.format_share()}\n")
        else:
            self._write(out, f"Parent - '{self.name}'\n")

    def write_users(self, out):
        # self._write(out, f"Parent - '{self.name}'\n")
        self.write(out)
        for user in self.users.values():
            user.write(out)


class SlurmUser(SlurmBase):
    """Create a new SlurmUser by parsing a line from sacctmgr dump. For
    example: User - 'jdoe':DefaultAccount='doe_lab':Fairshare=100:MaxSubmitJobs=101"""

    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmUser by parsing a line from sacctmgr dump. For
        example: User - 'jane':DefaultAccount='physics':Fairshare=Parent:QOS='general-compute'"""
        if not re.match("^User - '[^']+'", line):
            raise SlurmParserError(f'Invalid format. Must start with "User" for line: {line}')

        parts = line.split(':')
        name = re.sub(r"^User - ", '', parts[0]).strip("\n'")
        if len(name) == 0:
            raise SlurmParserError(f'User name not found for line: {line}')

        return SlurmUser(name, specs=parts[1:])

    def write(self, out):
        self._write(out, f"   User - {self.name} - Specs: {self.format_specs()} - Share: {self.format_share()}\n")
