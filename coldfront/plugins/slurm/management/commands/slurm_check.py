import logging
import os
import sys
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.slurm.associations import SlurmCluster
from coldfront.plugins.slurm.utils import (SLURM_ACCOUNT_ATTRIBUTE_NAME,
                                           SLURM_CLUSTER_ATTRIBUTE_NAME,
                                           SLURM_USER_SPECS_ATTRIBUTE_NAME,
                                           SlurmError, slurm_add_account,
                                           slurm_add_assoc, slurm_dump_cluster,
                                           slurm_remove_account,
                                           slurm_remove_assoc)

SLURM_IGNORE_USERS = import_from_settings('SLURM_IGNORE_USERS', [])
SLURM_IGNORE_ACCOUNTS = import_from_settings('SLURM_IGNORE_ACCOUNTS', [])
SLURM_IGNORE_CLUSTERS = import_from_settings('SLURM_IGNORE_CLUSTERS', [])
SLURM_NOOP = import_from_settings('SLURM_NOOP', False)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check consistency between Slurm associations and ColdFront allocations'

    def add_arguments(self, parser):
        parser.add_argument(
            "-i", "--input", help="Path to sacctmgr dump flat file as input. Defaults to stdin")
        parser.add_argument("-c", "--cluster",
                            help="Run sacctmgr dump [cluster] as input")
        parser.add_argument(
            "-s", "--sync", help="Remove associations in Slurm that no longer exist in ColdFront", action="store_true")
        parser.add_argument(
            "-n", "--noop", help="Print commands only. Do not run any commands.", action="store_true")
        parser.add_argument("-u", "--username", help="Check specific username")
        parser.add_argument("-a", "--account", help="Check specific account")
        parser.add_argument(
            "-x", "--header", help="Include header in output", action="store_true")

    def write(self, data):
        try:
            self.stdout.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def _skip_user(self, user, account):
        if user in SLURM_IGNORE_USERS:
            logger.debug("Ignoring user %s", user)
            return True

        if account in SLURM_IGNORE_ACCOUNTS:
            logger.debug("Ignoring account %s", account)
            return True

        if self.filter_account and account != self.filter_account:
            return True

        if self.filter_user and user != self.filter_user:
            return True

        return False

    def _skip_account(self, account):
        if account in SLURM_IGNORE_ACCOUNTS:
            logger.debug("Ignoring account %s", account)
            return True

        if self.filter_user:
            return True

        if self.filter_account and account != self.filter_account:
            return True

        return False

    def remove_user(self, user, account, cluster):
        if self._skip_user(user, account):
            return

        if self.sync:
            try:
                slurm_remove_assoc(user, cluster, account, noop=self.noop)
            except SlurmError as e:
                logger.error(
                    "Failed removing Slurm association user %s account %s cluster %s: %s", user, account, cluster, e)
            else:
                logger.error(
                    "Removed Slurm association user %s account %s cluster %s successfully", user, account, cluster)

        row = [
            user,
            account,
            cluster,
            'Remove',
        ]

        self.write('\t'.join(row))

    def remove_account(self, account, cluster):
        if self._skip_account(account):
            return

        if self.sync:
            try:
                slurm_remove_account(cluster, account, noop=self.noop)
            except SlurmError as e:
                logger.error(
                    "Failed removing Slurm account %s cluster %s: %s", account, cluster, e)
            else:
                logger.error(
                    "Removed Slurm account %s cluster %s successfully", account, cluster)

        row = [
            '',
            account,
            cluster,
            'Remove',
        ]

        self.write('\t'.join(row))

    def add_user(self, user, account, cluster, specs):
        if self._skip_user(user, account):
            return

        if self.sync:
            try:
                spec_list = []
                if len(specs) > 0:
                    spec_list = specs.split(':')
                slurm_add_assoc(user, cluster, account,
                                specs=spec_list, noop=self.noop)
            except SlurmError as e:
                logger.error(
                    "Failed adding Slurm association user %s account %s cluster %s: %s", user, account, cluster, e)
            else:
                logger.error(
                    "Added Slurm association user %s account %s cluster %s successfully", user, account, cluster)

        row = [
            user,
            account,
            cluster,
            'Add',
        ]

        self.write('\t'.join(row))

    def add_account(self, account, cluster, specs):
        if self._skip_account(account):
            return

        if self.sync:
            try:
                spec_list = []
                if len(specs) > 0:
                    spec_list = specs.split(':')
                slurm_add_account(cluster, account,
                                  specs=spec_list, noop=self.noop)
            except SlurmError as e:
                logger.error(
                    "Failed adding Slurm account %s cluster %s: %s", account, cluster, e)
            else:
                logger.error(
                    "Added Slurm account %s cluster %s successfully", account, cluster)

        row = [
            '',
            account,
            cluster,
            'Add',
        ]

        self.write('\t'.join(row))

    def _diff(self, cluster_a, cluster_b, action):
        for name, account in cluster_a.accounts.items():
            if name in cluster_b.accounts:
                total = 0
                for uid, user in account.users.items():
                    if uid not in cluster_b.accounts[name].users:
                        if action == 'Remove':
                            self.remove_user(uid, name, cluster_a.name)
                        elif action == 'Add':
                            self.add_user(
                                uid, name, cluster_a.name, user.format_specs())
                        total += 1

                if action == 'Remove' and total == len(account.users):
                    self.remove_account(name, cluster_a.name)
            else:
                if action == 'Add':
                    self.add_account(name, cluster_a.name,
                                     account.format_specs())

                for uid, user in account.users.items():
                    if action == 'Remove':
                        self.remove_user(uid, name, cluster_a.name)
                    elif action == 'Add':
                        self.add_user(uid, name, cluster_a.name,
                                      user.format_specs())

                if action == 'Remove':
                    self.remove_account(name, cluster_a.name)

    def check_consistency(self, slurm_cluster, coldfront_cluster):
        # Check for accounts in Slurm NOT in ColdFront
        self._diff(slurm_cluster, coldfront_cluster, 'Remove')

        # Check for accounts in Colfront NOT in Slurm
        self._diff(coldfront_cluster, slurm_cluster, 'Add')

    def _cluster_from_dump(self, cluster):
        slurm_cluster = None
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'cluster.cfg')
            try:
                slurm_dump_cluster(cluster, fname)
                with open(fname) as fh:
                    slurm_cluster = SlurmCluster.new_from_stream(fh)
            except SlurmError as e:
                logger.error("Failed to dump Slurm cluster %s: %s", cluster, e)

        return slurm_cluster

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARN)

        self.sync = False
        if options['sync']:
            self.sync = True
            logger.warn("Syncing Slurm with ColdFront")

        self.noop = SLURM_NOOP
        if options['noop']:
            self.noop = True
            logger.warn("NOOP enabled")

        if options['cluster']:
            slurm_cluster = self._cluster_from_dump(options['cluster'])
        elif options['input']:
            with open(options['input']) as fh:
                slurm_cluster = SlurmCluster.new_from_stream(fh)
        else:
            slurm_cluster = SlurmCluster.new_from_stream(sys.stdin)

        if not slurm_cluster:
            logger.error("Failed to import existing Slurm associations")
            sys.exit(1)

        if slurm_cluster.name in SLURM_IGNORE_CLUSTERS:
            logger.warn("Ignoring cluster %s. Nothing to do.",
                        slurm_cluster.name)
            sys.exit(0)

        try:
            resource = ResourceAttribute.objects.get(
                resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME, value=slurm_cluster.name).resource
        except ResourceAttribute.DoesNotExist:
            logger.error("No Slurm '%s' cluster resource found in ColdFront using '%s' attribute",
                         slurm_cluster.name, SLURM_CLUSTER_ATTRIBUTE_NAME)
            sys.exit(1)

        header = [
            'username',
            'account',
            'cluster',
            'slurm_action',
        ]

        if options['header']:
            self.write('\t'.join(header))

        self.filter_user = options['username']
        self.filter_account = options['account']

        coldfront_cluster = SlurmCluster.new_from_resource(resource)

        self.check_consistency(slurm_cluster, coldfront_cluster)
