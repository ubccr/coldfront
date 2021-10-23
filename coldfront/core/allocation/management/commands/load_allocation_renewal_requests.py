from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
from coldfront.core.project.utils_.renewal_utils import has_non_denied_renewal_request
from coldfront.core.user.models import EmailAddress
from coldfront.core.utils.common import utc_now_offset_aware
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import json
import logging
import os

"""An admin command that loads completed AllocationRenewalRequests from
a JSON file."""


class Command(BaseCommand):

    help = 'Create completed AllocationRenewalRequests from a JSON.'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            'json',
            help=(
                'The path to the JSON file containing a list of lists, where '
                'each inner list is a pair containing a PI\'s name and the '
                'name of the Project their allowance was renewed under.'),
            type=self.existent_file)
        parser.add_argument(
            '--dry_run', action='store_true',
            help='Display updates without performing them.')

    def handle(self, *args, **options):
        """Process the input JSON. Create requests for valid pairs, or
        display what requests would be created (if dry_run)."""
        file_path = options['json']
        allocation_period = get_current_allocation_period()
        valid, already_renewed, invalid = self.parse_input_file(
            file_path, allocation_period)
        self.process_valid_pairs(valid, allocation_period, options['dry_run'])
        self.process_already_renewed_pis(already_renewed, allocation_period)
        self.process_invalid_pairs(invalid)

    @staticmethod
    def existent_file(path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'Invalid path {path}.')
        if not os.path.isfile(path):
            raise IsADirectoryError(f'Invalid file {path}.')
        return path

    @staticmethod
    def parse_input_file(file_path, allocation_period):
        """Given a path to a JSON input file and an AllocationPeriod,
        partition the entries into three lists: (1) valid (PI User,
        Project, Requester User) tuples, (2) Users that have already
        renewed, and (3) invalid input tuples."""
        with open(file_path, 'r') as f:
            pairs = json.load(f)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        valid, already_renewed, invalid = [], [], []
        for pi_name, project_name, requester_email, _ in pairs:
            try:
                project = Project.objects.prefetch_related(
                    'projectuser_set').get(name=project_name)
            except Project.DoesNotExist:
                invalid.append((pi_name, project_name, requester_email))
                continue
            pi_name_parts = pi_name.split()
            first_name, last_name = pi_name_parts[0], pi_name_parts[-1]
            try:
                pi_user = User.objects.get(
                    first_name=first_name, last_name=last_name)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                invalid.append((pi_name, project_name, requester_email))
                continue
            try:
                project.projectuser_set.get(
                    role=pi_role, status=active_project_user_status,
                    user=pi_user)
            except ProjectUser.DoesNotExist:
                invalid.append((pi_name, project_name, requester_email))
                continue
            if has_non_denied_renewal_request(pi_user, allocation_period):
                already_renewed.append(pi_user)
                continue
            # Retrieve the requester by email address. If none exists, use the
            # PI as the requester.
            try:
                email_address = EmailAddress.objects.get(email=requester_email)
            except EmailAddress.DoesNotExist:
                requester_user = pi_user
            else:
                requester_user = email_address.user
            valid.append((pi_user, project, requester_user))
        return valid, already_renewed, invalid

    def process_already_renewed_pis(self, already_renewed, allocation_period):
        """Given a list of PI Users, where the PI has already renewed
        their allocation during the given AllocationPeriod, write to
        stdout."""
        for pi_user in already_renewed:
            pi_str = (
                f'{pi_user.first_name} {pi_user.last_name} ({pi_user.email})')
            message = (
                f'PI {pi_str} has already renewed their allocation during '
                f'AllocationPeriod {allocation_period.name}. Skipping.')
            self.stdout.write(self.style.WARNING(message))

    def process_invalid_pairs(self, invalid_pairs):
        """Given a list of (pi_name, project_name, requester_user)
        tuples, where the PI and/or the Project are not valid, write to
        stderr."""
        for pi_name, project_name, requester_email in invalid_pairs:
            message = (
                f'Invalid tuple: ({pi_name}, {project_name}, '
                f'{requester_email}). Skipping.')
            self.stderr.write(self.style.ERROR(message))

    def process_valid_pairs(self, valid, allocation_period, dry_run):
        """Given a list of valid (PI User, Project, Requester User)
        pairs, create an AllocationRenewalRequest under the given
        AllocationPeriod with status 'Complete', and write to stdout.

        If dry_run is True, write the triple to stdout without creating
        the request."""
        complete_renewal_status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        for pi_user, project, requester_user in valid:
            requester_str = (
                f'{requester_user.first_name} {requester_user.last_name} '
                f'({requester_user.email})')
            pi_str = (
                f'{pi_user.first_name} {pi_user.last_name} ({pi_user.email})')
            if dry_run:
                message = (
                    f'Would create pre-completed AllocationRenewalRequest for '
                    f'PI {pi_str}, Project {project.name}, requester '
                    f'{requester_str}, and AllocationPeriod '
                    f'{allocation_period.name}.')
                self.stdout.write(self.style.WARNING(message))
                continue
            try:
                request = AllocationRenewalRequest.objects.create(
                    requester=requester_user,
                    pi=pi_user,
                    allocation_period=allocation_period,
                    status=complete_renewal_status,
                    pre_project=project,
                    post_project=project)
                request.state['eligibility']['status'] = 'Approved'
                request.state['eligibility']['timestamp'] = \
                    utc_now_offset_aware().isoformat()
                request.save()
            except Exception as e:
                message = (
                    f'Failed to create AllocationRenewalRequest for PI '
                    f'{pi_str}, Project {project.name}, and requester '
                    f'{requester_str}.')
                self.stderr.write(self.style.ERROR(message))
                self.logger.exception(e)
            else:
                message = (
                    f'Created pre-completed AllocationRenewalRequest '
                    f'{request.pk} for PI {pi_str}, Project {project.name}, '
                    f'requester {requester_str} and AllocationPeriod '
                    f'{allocation_period.name}.')
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
