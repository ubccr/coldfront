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
                                           SlurmError, slurm_remove_qos,
                                           slurm_dump_cluster, slurm_remove_account,
                                           slurm_remove_assoc)

SLURM_IGNORE_USERS = import_from_settings('SLURM_IGNORE_USERS', [])
SLURM_IGNORE_ACCOUNTS = import_from_settings('SLURM_IGNORE_ACCOUNTS', [])
SLURM_IGNORE_CLUSTERS = import_from_settings('SLURM_IGNORE_CLUSTERS', [])
SLURM_NOOP = import_from_settings('SLURM_NOOP', False)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Issues Slurm commands to bring the Slurm database (as given by the \
        input Slurm sacctmgr dump flat file) to match what is in ColdFront.'

    def add_arguments(self, parser):
        parser.add_argument(
            "-i", "--input", help="Path to sacctmgr dump flat file as input. Defaults to stdin")
        parser.add_argument("-c", "--cluster",
                            help="Run sacctmgr dump [cluster] as input")
        parser.add_argument(
            "-n", "--noop", help="Print commands only. Do not run any commands.", action="store_true")
        #parser.add_argument("-u", "--username", help="Check specific username")
        #parser.add_argument("-a", "--account", help="Check specific account")
        parser.add_argument("-f", "--flags", default=[], action='append',
            help="Flags controlling behavior.  Repeat for multiple flags. See help_flags for more info.")
        parser.add_argument("--help_flags", "--help-flags", action='store_true',
            help="Just display help text on flags.")
        parser.add_argument("--reverse", action='store_true',
            help="Reverse mode: issue commands to make ColdFront match dump file.")

    def _cluster_from_dump(self, cluster):
        """Issue sacctmgr dump to get our SlurmCluster structure."""
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

    def help_flags(self):
        """Output help text describing flags."""
        sys.stderr.write('The following flags can be used to control the\n')
        sys.stderr.write('behavior of the script.  Recognized values are:\n')
        sys.stderr.write('    skip_create_cluster: when set, do not create\n')
        sys.stderr.write('        the cluster if missing.  If set and the\n')
        sys.stderr.write('        cluster is missing, just return (accounts\n')
        sys.stderr.write('        and users in the missing cluster will not\n')
        sys.stderr.write('        be created either)\n')
        sys.stderr.write('    skip_delete_cluster: when set, do not delete\n')
        sys.stderr.write('        the cluster if missing in ColdFront.  If\n')
        sys.stderr.write('        set and the cluster is missing in\n')
        sys.stderr.write('        ColdFront, just return (accounts and users\n')
        sys.stderr.write('        will not be deleted either)\n')
        sys.stderr.write('    force_delete_cluster: normally the script\n')
        sys.stderr.write('        will not delete a cluster even if it\n')
        sys.stderr.write('        should.  Only if this is set will the\n')
        sys.stderr.write('        code delete the cluster.\n')
        sys.stderr.write('    skip_cluster_specs: when set, do not compare\n')
        sys.stderr.write('        the cluster specs.\n')
        sys.stderr.write('    skip_create_account: when set, if the account\n')
        sys.stderr.write('        is missing in Slurm, the script will not\n')
        sys.stderr.write('        the account (or any users belonging to the\n')
        sys.stderr.write('        account\n')
        sys.stderr.write('    skip_delete_account: when set, if the account\n')
        sys.stderr.write('        is missing in ColdFront, do not delete\n')
        sys.stderr.write('        the account (or users in the account)\n')
        sys.stderr.write('    skip_account_specs: when set, do not compare\n')
        sys.stderr.write('        the account specs.\n')
        sys.stderr.write('    skip_create_user: when set, do not create\n')
        sys.stderr.write('        an user if missing in Slurm.\n')
        sys.stderr.write('    skip_delete_user: when set, do not delete\n')
        sys.stderr.write('        user if missing in ColdFront.\n')
        sys.stderr.write('    skip_user_specs: when set, do not compare\n')
        sys.stderr.write('        the user specs.\n')
        sys.stderr.write('    ignore_<spec_field>: when set, the compare\n')
        sys.stderr.write('        routine will ignore the value of the\n')
        sys.stderr.write('        spec named <spec_field>.  For set/TRES\n')
        sys.stderr.write('        valued specs, the entire field is ignored.\n')
        sys.stderr.write('    ignore_<spec_field>_<subfld>: when set and\n')
        sys.stderr.write('        <spec_field> is TRES valued, the TRES\n')
        sys.stderr.write('        named <tag> will be ignored by the\n')
        sys.stderr.write('        comparison routines.\n')
        sys.stderr.write('\n')
        sys.stderr.write('The strings are case insensitive, and multiple\n')
        sys.stderr.write('flags can be given by repeating the --flag argument.\n')

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

        if options['help_flags']:
            self.help_flags()
            return

        self.noop = SLURM_NOOP
        if options['noop']:
            self.noop = True
            logger.warn("NOOP enabled")

        if options['cluster']:
            if options['input']:
                logger.error("Arguments 'cluster' and 'input' are mutually exclusive.")
                sys.exit(1)
            slurm_cluster = self._cluster_from_dump(options['cluster'])
        elif options['input']:
            with open(options['input']) as fh:
                slurm_cluster = SlurmCluster.new_from_stream(fh)
        else:
            logger.error("Exactly one of 'cluster' or 'input' required.")
            sys.exit(1)
            #slurm_cluster = SlurmCluster.new_from_stream(sys.stdin)

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

        coldfront_cluster = SlurmCluster.new_from_resource(
            resource, addroot=True)

        # Fix flags: lowercase and replace - with _
        flags = list(map(lambda flag: flag.lower(), options['flags']))
        flags = list(map(lambda flag: flag.replace('-','_'), flags))

        if options['reverse']:
            coldfront_cluster.update_cluster_to(
                old=coldfront_cluster,
                new=slurm_cluster,
                flags=flags,
                noop=self.noop)
        else:
            coldfront_cluster.update_cluster_to(
                old=slurm_cluster,
                new=coldfront_cluster,
                flags=flags,
                noop=self.noop)
        

