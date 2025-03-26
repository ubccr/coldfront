import logging
import os
import sys
import tempfile

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from coldfront.core.project.models import (
    Project,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectStatusChoice,
)
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.allocation.models import (
    Allocation,
    AllocationUser,
    AllocationAttribute,
    AllocationStatusChoice,
    AllocationAttributeType,
    AllocationUserStatusChoice,
)
from coldfront.plugins.slurm.utils import (
    SLURM_ACCOUNT_ATTRIBUTE_NAME,
    SLURM_CLUSTER_ATTRIBUTE_NAME,
    SLURM_USER_SPECS_ATTRIBUTE_NAME,
    SlurmError,
    slurm_dump_cluster,
)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.slurm.associations import SlurmCluster

SLURM_IGNORE_USERS = import_from_settings('SLURM_IGNORE_USERS', [])
SLURM_IGNORE_ACCOUNTS = import_from_settings('SLURM_IGNORE_ACCOUNTS', [])
SLURM_IGNORE_CLUSTERS = import_from_settings('SLURM_IGNORE_CLUSTERS', [])
SLURM_NOOP = import_from_settings('SLURM_NOOP', False)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command that imports from an sacctmgr dump into the ColdFront database."""

    help = "Check consistency between Slurm associations and ColdFront allocations"

    def add_arguments(self, parser):
        # Input args
        parser.add_argument(
            "-i",
            "--input",
            help="Path to sacctmgr dump flat file as input. Defaults to stdin",
        )
        parser.add_argument(
            "-c", "--cluster", help="Run sacctmgr dump [cluster] as input"
        )

        # Project defaults
        parser.add_argument(
            "-p",
            "--default-pi",
            help="Set the default principle investigator's username for new projects.",
            default="no_pi",
            dest="default_pi",
        )
        parser.add_argument(
            "-f",
            "--default-fos",
            help="Set the default field of science for new projects. Specify as the ID/primary key in the database.",
            default=149,
            dest="default_fos",
            type=int,
        )
        parser.add_argument(
            "-t",
            "--default-status",
            help="Set the default project status for new projects. Specify as the ID/primary key in the database",
            default=1,
            dest="default_status",
            type=int,
        )
        force_review = parser.add_mutually_exclusive_group()
        force_review.add_argument(
            "--force-review",
            help="Specifying this marks force_review for new projects to be true. Incompatible with --no-force-review. If not specified, defaults to false.",
            action="store_true",
            dest="force_review",
        )
        force_review.add_argument(
            "--no-force-review",
            help="Specifying this marks force_review for new projects to be false. Incompatible with --force-review.",
            action="store_false",
            dest="force_review",
        )
        requires_review = parser.add_mutually_exclusive_group()
        requires_review.add_argument(
            "--no-requires-review",
            help="Specifying this marks requires_review for new projects to be false. Incompatible with --requires-review. if not specified, defaults to true.",
            action="store_false",
            dest="requires_review",
        )
        requires_review.add_argument(
            "--requires-review",
            help="Specifying this marks requires_review for new projects to be true. Incompatible with --no-requires-review.",
            action="store_true",
            dest="requires_review",
        )

        # ProjectUser defaults
        parser.add_argument(
            "--project-user-role",
            help="Set the default project user role. Specify as the ID/primary key in the database.",
            default=1,
            dest="pu_role",
            type=int,
        )
        parser.add_argument(
            "--project-user-status",
            help="Set the default project user status. Specify as the ID/primary key in the database.",
            default=1,
            dest="pu_status",
            type=int,
        )
        pu_notifs = parser.add_mutually_exclusive_group()
        pu_notifs.add_argument(
            "--project-user-no-notifs",
            help="Specifying this marks enable_notifications for new project users to be false. Incompatible with --project-user-notifs. If not specified, defaults to true.",
            action="store_false",
            dest="pu_notifs",
        )
        pu_notifs.add_argument(
            "--project-user-notifs",
            help="Specifying this marks enable_notifications for new project users to be true. Incompatible with --project-user-no-notifs.",
            action="store_true",
            dest="pu_notifs",
        )

        # Allocation defaults
        parser.add_argument(
            "--allocation_status",
            help="Set the default allocation status. Specify as the ID/primary key in the database.",
            default=1,
            dest="alloc_status",
            type=int,
        )
        parser.add_argument(
            "--allocation_user_status",
            help="Set the default allocation user status. Specify as the ID/primary key in the database.",
            default=1,
            dest="alloc_user_status",
            type=int,
        )

        # Misc
        parser.add_argument(
            "-n",
            "--noop",
            help="Print operations only. Do not preform any operations.",
            action="store_true",
        )

    def _skip_user(self, user, account):
        if user in SLURM_IGNORE_USERS:
            logger.debug("Ignoring user %s", user)

        if account in SLURM_IGNORE_ACCOUNTS:
            logger.debug("Ignoring account %s", account)
            return True

        return False

    def coldfront_get_user(self, username, account):
        """
        Get or create user in the ColdFront database.

        :returns User object or None if noop
        """
        if self._skip_user(username, account):
            return
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            kwargs = {"username": username}
            if self.noop:
                logger.warn(f"NOOP - Create User {kwargs}")
                return None
            else:
                return User.objects.create(**kwargs)

    def add_user(self, username, account, cluster_name, qos_spec):
        """Add a user to the ColdFront database."""
        if self._skip_user(username, account):
            return

        user = self.coldfront_get_user(username, account)
        project = self.coldfront_get_project(account)
        _project_user = self.coldfront_get_project_user(user, project)
        allocation = self.coldfront_get_allocation(project)
        _allocation_user = self.coldfront_get_allocation_user(allocation, user)
        _qoses = self.coldfront_get_allocation_attribute(allocation, self.user_specs_attr, qos_spec)
        return (user, project, allocation)

    def coldfront_get_allocation(self, project):
        """
        Get or create the Allocation assocated with the given project and assigns it the approporiate cluster resource.

        :returns Allocation object or None if noop
        """
        alloc_kwargs = {
            "project": project,
            "status": self.alloc_status,
        }
        if project is None:
            logger.warn(f"NOOP - create Allocation {alloc_kwargs}")
            return None

        alloc = None
        try:
            alloc = Allocation.objects.get(project=project)
        except Allocation.DoesNotExist:
            if self.noop:
                logger.warn(f"NOOP - create Allocation {alloc_kwargs}")
            else:
                alloc = Allocation.objects.create(**alloc_kwargs)
        self.coldfront_get_allocation_attribute(alloc, self.acct_name_attr, project.title)
        self.coldfront_assign_allocation_resource(alloc, alloc_kwargs)
        return alloc

    def coldfront_get_allocation_user(self, allocation, user):
        """
        Get or create an AllocationUser in the ColdFront database.

        :returns AllocationUser object or None if noop
        """
        kwargs = {
            "allocation": allocation,
            "user": user,
            "status": self.alloc_user_status,
        }
        if allocation is None or user is None:
            logger.warn(f"NOOP - Create AllocationUser {kwargs}")
            return None
        try:
            return AllocationUser.objects.get(allocation=allocation, user=user)
        except AllocationUser.DoesNotExist:
            return AllocationUser.objects.create(**kwargs)

    def coldfront_get_allocation_attribute(
        self, allocation, allocation_attribute_type, value
    ):
        """
        Get or create the AllocationAttribute assocated with the given allocation.

        :returns AllocationAttribute object or None if noop
        """
        kwargs = {
            "allocation_attribute_type": allocation_attribute_type,
            "allocation": allocation,
            "value": value,
        }
        if allocation is None or allocation_attribute_type is None or value is None:
            logger.warn(f"NOOP - create AllocationAttribute {kwargs}")
            return None
        try:
            return AllocationAttribute.objects.get(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation,
            )
        except AllocationAttribute.DoesNotExist:
            if self.noop:
                logger.warn(f"NOOP - create AllocationAttribute {kwargs}")
                return None
            else:
                return AllocationAttribute.objects.create(**kwargs)

    def coldfront_assign_allocation_resource(self, allocation, alloc_kwargs):
        """Assign the cluster resource to the given allocation. Does nothing if noop or if already assigned."""
        if allocation is None:
            logger.warn(
                f"NOOP - add Resource {self.resource} to Allocation {alloc_kwargs}"
            )
            return
        allocation.resources.add(self.resource)
        allocation.save()

    def coldfront_get_project_user(self, user, project):
        """
        Get or create a ProjectUser in the ColdFront database.

        :returns ProjectUser object or None if noop
        """
        kwargs = {
            "user": user,
            "project": project,
            "role": self.pu_role,
            "status": self.pu_status,
            "enable_notifications": self.pu_notifs,
        }
        if user is None or project is None and self.noop:
            logger.warn(f"NOOP - create ProjectUser {kwargs}")
            return None
        try:
            return ProjectUser.objects.get(user=user, project=project)
        except ProjectUser.DoesNotExist:
            if self.noop:
                logger.warn(f"NOOP - create ProjectUser {kwargs}")
                return None
            else:
                return ProjectUser.objects.create(**kwargs)

    def coldfront_get_project(self, account):
        """
        Get or create user in the ColdFront database.

        :returns Project object or None if noop
        """
        try:
            return Project.objects.get(title=account)
        except Project.DoesNotExist:
            kwargs = {
                "title": account,
                "pi": self.default_pi,
                "description": "",
                "field_of_science": self.default_fos,
                "status": self.default_status,
                "force_review": self.force_review,
                "requires_review": self.requires_review,
            }
            if self.noop:
                logger.warn(f"NOOP - Create Project {kwargs}")
                return None
            else:
                return Project.objects.create(**kwargs)

    def _parse_qos(self, qos):
        if qos.startswith('QOS+='):
            qos = qos.replace('QOS+=', '')
            qos = qos.replace("'", '')
            return qos.split(',')
        elif qos.startswith('QOS='):
            qos = qos.replace('QOS=', '')
            qos = qos.replace("'", '')
            lst = []
            for q in qos.split(','):
                if q.startswith('+'):
                    lst.append(q.replace('+', ''))
            return lst

        return []

    def import_to_coldfront(self, slurm_cluster):
        """
        Import the provided cluster into the ColdFront database.

        :param slurm_cluster: The SlurmCluster object to import.
        """
        for name, account in slurm_cluster.accounts.items():
            if name == "root":
                continue

            logger.debug(f"{name}, {account}")
            for uid, user in account.users.items():
                if uid == "root":
                    continue
                qos_spec = next(
                    filter(
                        lambda spec: spec.startswith("QOS"),
                        user.spec_list()
                    )
                )
                user, project, allocation = self.add_user(
                    uid, name, slurm_cluster.name, qos_spec
                )

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

        logger.warn("Syncing ColdFront with Slurm")

        self.default_pi = User.objects.get_or_create(username=options['default_pi'])[0]
        self.default_fos = FieldOfScience.objects.get(pk=options['default_fos'])
        self.default_status = ProjectStatusChoice.objects.get(pk=options['default_status'])
        self.force_review = options['force_review']
        self.requires_review = options['requires_review']

        self.pu_role = ProjectUserRoleChoice.objects.get(pk=options['pu_role'])
        self.pu_status = ProjectUserStatusChoice.objects.get(pk=options['pu_status'])
        self.pu_notifs = options['pu_notifs']

        self.alloc_status = AllocationStatusChoice.objects.get(pk=options['alloc_status'])
        self.alloc_user_status = AllocationUserStatusChoice.objects.get(pk=options['alloc_user_status'])

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
            self.resource = ResourceAttribute.objects.get(
                resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME,
                value=slurm_cluster.name,
            ).resource
        except ResourceAttribute.DoesNotExist:
            logger.error(
                "No Slurm '%s' cluster resource found in ColdFront using '%s' attribute",
                slurm_cluster.name,
                SLURM_CLUSTER_ATTRIBUTE_NAME,
            )
            sys.exit(1)

        try:
            self.acct_name_attr = AllocationAttributeType.objects.get(
                name=SLURM_ACCOUNT_ATTRIBUTE_NAME
            )
        except AllocationAttributeType.DoesNotExist:
            logger.error(
                "No AllocationAttributeType '%s' found in ColdFront",
                SLURM_ACCOUNT_ATTRIBUTE_NAME,
            )
            sys.exit(1)

        try:
            self.user_specs_attr = AllocationAttributeType.objects.get(
                name=SLURM_USER_SPECS_ATTRIBUTE_NAME
            )
        except AllocationAttributeType.DoesNotExist:
            logger.error(
                "No AllocationAttributeType '%s' found in ColdFront",
                SLURM_ACCOUNT_ATTRIBUTE_NAME,
            )
            sys.exit(1)

        self.import_to_coldfront(slurm_cluster)
