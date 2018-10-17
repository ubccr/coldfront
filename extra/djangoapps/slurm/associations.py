import datetime
import re

from core.djangoapps.resources.models import Resource

from extra.djangoapps.slurm.utils import SLURM_CLUSTER_ATTRIBUTE_NAME, \
              SLURM_ACCOUNT_ATTRIBUTE_NAME, SLURM_SPECS_ATTRIBUTE_NAME, SLURM_USER_SPECS_ATTRIBUTE_NAME

class SlurmError(Exception):
    pass

class SlurmParserError(SlurmError):
    pass

class SlurmBase:
    def __init__(self, name, specs=None):
        if specs is None:
            specs = []

        self.name = name
        self.specs = specs

    def format_specs(self):
        """Format unique list of Slurm Specs"""
        items = []
        for s in self.specs:
            for i in s.split(':'):
                items.append(i)

        return ':'.join([x for x in list(set(items))])
    
class SlurmCluster(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.accounts = {}

    @staticmethod
    def new_from_stream(stream):
        """Create a new SlurmCluster by parsing the output from sacctmgr dump."""
        cluster = None
        parent = None
        for line in stream:
            line = line.strip()
            if re.match("^#", line):
                continue
            elif re.match("^Cluster - '[^']+'", line):
                parts = line.split(':')
                name = re.sub(r"^Cluster - ", '', parts[0]).strip("\n'")
                if len(name) == 0:
                    raise(SlurmParserError('Cluster name not found for line: {}'.format(line)))
                cluster = SlurmCluster(name)
                cluster.specs += parts[1:]
            elif re.match("^Account - '\w+'", line):
                account = SlurmAccount.new_from_sacctmgr(line)
                cluster.accounts[account.name] = account
            elif re.match("^Parent - '\w+'", line):
                parent = re.sub(r"^Parent - ", '', line).strip("\n'")
                if parent == 'root':
                    cluster.accounts['root'] = SlurmAccount('root')
                if not parent:
                    raise(SlurmParserError('Parent name not found for line: {}'.format(line)))
            elif re.match("^User - '\w+'", line):
                user = SlurmUser.new_from_sacctmgr(line)
                if not parent:
                    raise(SlurmParserError('Found user record without Parent for line: {}'.format(line)))
                account = cluster.accounts[parent]
                account.add_user(user)
                cluster.accounts[parent] = account
                        
        if not cluster or not cluster.name:
            raise(SlurmParserError('Failed to parse Slurm cluster name. Is this in sacctmgr dump file format?'))
            
        return cluster

    @staticmethod
    def new_from_resource(resource):
        """Create a new SlurmCluster from a Coldfront Resource model."""
        name = resource.get_attribute(SLURM_CLUSTER_ATTRIBUTE_NAME)
        specs = resource.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
        if not name:
            raise(SlurmError('Resource {} missing slurm_cluster'.format(resource)))

        cluster = SlurmCluster(name, specs)

        # Process subscriptions
        for sub in resource.subscription_set.filter(status__name='Active'):
            cluster.add_subscription(sub)

        # Process child resources
        children = Resource.objects.filter(parent_resource_id=resource.id, resource_type__name='Cluster Partition')
        for r in children:
            partition_specs = r.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
            for sub in r.subscription_set.filter(status__name='Active'):
                cluster.add_subscription(sub, specs=partition_specs)

        return cluster

    def add_subscription(self, sub, specs=None):
        if specs is None:
            specs = []

        """Add accounts from a Coldfront Subscription model to SlurmCluster"""
        name = sub.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = 'root'

        account = self.accounts.get(name, SlurmAccount(name))
        account.add_subscription(sub)
        account.specs += specs
        self.accounts[name] = account

    def write(self, out):
        out.write("# Coldfront Subscription Slurm assocations dump {}\n".format(datetime.datetime.now().date()))
        out.write("Cluster - '{}':{}\n".format(
            self.name,
            self.format_specs(),
        ))
        if 'root' in self.accounts:
            self.accounts['root'].write(out)
        else:
            out.write("Parent - 'root'\n")

        for name, account in self.accounts.items():
            if account.name == 'root':
                continue
            account.write(out)


class SlurmAccount(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.users = {}

    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmAccount by parsing a line from sacctmgr dump. For
        example: Account - 'physics':Description='physics group':Organization='cas':Fairshare=100"""
        if not re.match("^Account - '\w+'", line):
            raise(SlurmParserError('Invalid format. Must start with "Account" for line: {}'.format(line)))

        parts = line.split(':')
        name = re.sub(r"^Account - ", '', parts[0]).strip("\n'")
        if len(name) == 0:
            raise(SlurmParserError('Cluster name not found for line: {}'.format(line)))

        return SlurmAccount(name, specs=parts[1:])

    def add_subscription(self, sub):
        """Add users from a Coldfront Subscription model to SlurmAccount"""
        name = sub.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = 'root'

        if name != self.name:
            raise(SlurmError('Subscription {} slurm_account_name does not match {}'.format(sub, self.name)))

        self.specs += sub.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)

        user_specs = sub.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        for u in sub.subscriptionuser_set.filter(status__name='Active'):
            user = SlurmUser(u.user.username)
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
            out.write("Account - '{}':{}\n".format(
                self.name,
                self.format_specs(),
            ))

        out.write("Parent - '{}'\n".format(self.name))
        for uid, user in self.users.items():
            user.write(out)

class SlurmUser(SlurmBase):

    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmUser by parsing a line from sacctmgr dump. For
        example: User - 'jane':DefaultAccount='physics':Fairshare=Parent:QOS='general-compute'"""
        if not re.match("^User - '\w+'", line):
            raise(SlurmParserError('Invalid format. Must start with "User" for line: {}'.format(line)))

        parts = line.split(':')
        name = re.sub(r"^User - ", '', parts[0]).strip("\n'")
        if len(name) == 0:
            raise(SlurmParserError('User name not found for line: {}'.format(line)))

        return SlurmUser(name, specs=parts[1:])

    def write(self, out):
        out.write("User - '{}':{}\n".format(
            self.name,
            self.format_specs(),
        ))
