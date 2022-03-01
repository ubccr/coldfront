from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import next_allocation_start_datetime
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import get_project_compute_allocation
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_compute_resource_names
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet_data

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from coldfront.core.utils.common import utc_now_offset_aware
from django.core.validators import validate_email

import logging
import re


"""An admin command with subcommands that load existing LRC data from various
data sources."""


LAWRENCIUM_PROJECT_PREFIXES = ('ac_', 'lr_', 'pc_')


class Command(BaseCommand):

    help = 'Loads existing LRC data from provided data sources.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self.add_subparsers(subparsers)

    @staticmethod
    def add_subparsers(subparsers):
        """Add subcommands and their respective parsers."""

        def add_file_argument(parser, file_arg_name):
            """Add an argument to the given parser to accept a file
            path."""
            parser.add_argument(
                file_arg_name,
                help=f'The path to the {file_arg_name} file.',
                type=str)

        all_parser = subparsers.add_parser('all', help='Run all subcommands.')
        for name in ('passwd_file', 'group_file', 'billing_file'):
            add_file_argument(all_parser, name)

        allocations_parser = subparsers.add_parser(
            'allocations',
            help=(
                'Create allocation-related objects, referencing some data '
                'from the cluster group file.'))
        add_file_argument(allocations_parser, 'group_file')

        billing_ids_parser = subparsers.add_parser(
            'billing_ids',
            help='Load IDs to be used for monthly billing from a file.')
        add_file_argument(billing_ids_parser, 'billing_file')

        subparsers.add_parser(
            'project_pis_and_managers',
            help=(
                'Load Project PIs and Managers from a pre-defined '
                'spreadsheet.'))

        projects_and_project_users_parser = subparsers.add_parser(
            'projects_and_project_users',
            help=(
                'Load Projects and their ProjectUsers from the cluster group '
                'file.'))
        add_file_argument(projects_and_project_users_parser, 'group_file')

        users_parser = subparsers.add_parser(
            'users', help='Load users from the cluster passwd file.')
        add_file_argument(users_parser, 'passwd_file')

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_all(self, *args, **options):
        """Handle the 'all' subcommand."""
        ordered_subcommands = [
            'users',
            'projects_and_project_users',
            'project_pis_and_managers',
            'allocations',
            'billing_ids',
        ]
        for subcommand in ordered_subcommands:
            handler = getattr(self, f'handle_{subcommand}')
            handler(*args, **options)

    def handle_allocations(self, *args, **options):
        """Handle the 'allocations' subcommand."""
        usernames_by_project_name = self.get_project_and_project_users_data(
            options['group_file'])
        self.set_up_lawrencium_project_allocations(usernames_by_project_name)
        self.set_up_departmental_project_allocations(usernames_by_project_name)

    def handle_billing_ids(self, *args, **options):
        """Handle the 'billing_ids' subcommand."""

        def get_or_create_with_cache(model, key, cache,
                                     **get_or_create_kwargs):
            """Get or create an object of the given model with the given
            keyword arguments if the given key is not already in the
            given cache. Store the object in the cache and return it,
            along with whether an object was created."""
            object_created = False
            if key not in cache:
                cache[key], object_created = model.objects.get_or_create(
                    **get_or_create_kwargs)
            return cache[key], object_created

        billing_ids_data = self.get_billing_ids_data(options['billing_file'])
        user_account_fee_ids = billing_ids_data['user_account_fee_ids']
        job_usage_fee_id_users_by_project = billing_ids_data[
            'job_usage_fee_id_users_by_project']

        # Cache BillingProject and BillingActivity objects.
        bp_by_identifier = {}
        ba_by_identifier_pair = {}

        bp_defaults = {
            'description': 'Unknown, invalid project.',
        }
        ba_defaults = {
            'description': 'Unknown, invalid activity.',
            'is_valid': False,
        }

        for username, billing_id in user_account_fee_ids.items():
            bp_identifier, ba_identifier = billing_id.split('-')
            billing_project, created = get_or_create_with_cache(
                BillingProject, bp_identifier, bp_by_identifier,
                identifier=bp_identifier, defaults=bp_defaults)
            if created:
                self.logger.info(
                    f'Invalid, unknown BillingProject {bp_identifier} was '
                    f'created.')

            pair = (bp_identifier, ba_identifier)
            billing_activity, created = get_or_create_with_cache(
                BillingActivity, pair, ba_by_identifier_pair,
                billing_project=billing_project, identifier=ba_identifier,
                defaults=ba_defaults)
            if created:
                self.logger.info(
                    f'Invalid, unknown BillingActivity {billing_id} was '
                    f'created.')

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.logger.error(f'Invalid username {username}.')
                continue
            user.userprofile.billing_activity = billing_activity
            user.userprofile.save()
            self.logger.info(
                f'Set User {username}\'s billing ID for the monthly user '
                f'account fee to {billing_id}.')

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')

        for project_name in job_usage_fee_id_users_by_project:
            # The Project should already exist.
            try:
                project = Project.objects.get(name=project_name)
            except Project.DoesNotExist:
                self.logger.error(
                    f'Project {project_name} unexpectedly does not exist.')
                continue

            try:
                allocation = get_project_compute_allocation(project)
            except Allocation.DoesNotExist:
                self.logger.error(
                    f'Project {project_name} unexpectedly does not have an '
                    f'Allocation to a Compute Resource.')
                continue

            job_usage_fee_id_users = job_usage_fee_id_users_by_project[
                project_name]
            max_user_count = 0
            most_used_billing_activity = None
            for billing_id, usernames in job_usage_fee_id_users.items():
                bp_identifier, ba_identifier = billing_id.split('-')
                billing_project, created = get_or_create_with_cache(
                    BillingProject, bp_identifier, bp_by_identifier,
                    identifier=bp_identifier, defaults=bp_defaults)
                if created:
                    self.logger.info(
                        f'Invalid, unknown BillingProject {bp_identifier} was '
                        f'created.')

                pair = (bp_identifier, ba_identifier)
                billing_activity, created = get_or_create_with_cache(
                    BillingActivity, pair, ba_by_identifier_pair,
                    billing_project=billing_project, identifier=ba_identifier,
                    defaults=ba_defaults)
                if created:
                    self.logger.info(
                        f'Invalid, unknown BillingActivity {billing_id} was '
                        f'created.')

                if len(usernames) >= max_user_count:
                    max_user_count = len(usernames)
                    most_used_billing_activity = billing_activity

                for username in usernames:
                    try:
                        user = User.objects.get(username=username)
                    except User.DoesNotExist:
                        self.logger.error(f'Invalid username {username}.')
                        continue

                    try:
                        ProjectUser.objects.get(user=user, project=project)
                    except ProjectUser.DoesNotExist:
                        self.logger.info(
                            f'User {username} is not a member of Project '
                            f'{project_name}. Skipping.')
                        continue

                    try:
                        allocation_user = allocation.allocationuser_set.get(
                            user=user)
                    except AllocationUser.DoesNotExist:
                        self.logger.error(
                            f'User {username} is a member of Project '
                            f'{project_name}, but not its Compute Allocation.')
                        continue

                    set_allocation_user_attribute_value(
                        allocation_user, 'Billing Activity',
                        str(billing_activity.pk))
                    self.logger.info(
                        f'Set User {username}\'s billing ID for the monthly '
                        f'job usage fee under Project {project_name} to '
                        f'{billing_id}.')

            # Treat the BillingActivity used by the most Users on this Project
            # as its default.
            if max_user_count == 0:
                continue
            allocation_attribute_defaults = {
                'value': str(most_used_billing_activity.pk),
            }
            allocation_attribute, _ = \
                AllocationAttribute.objects.update_or_create(
                    allocation_attribute_type=allocation_attribute_type,
                    allocation=allocation,
                    defaults=allocation_attribute_defaults)
            default_billing_id = '-'.join([
                most_used_billing_activity.billing_project.identifier,
                most_used_billing_activity.identifier])
            self.logger.info(
                f'Set Project {project_name}\'s default billing ID to '
                f'{default_billing_id}.')

    def handle_project_pis_and_managers(self, *args, **options):
        """Handle the 'project_pis_and_managers' subcommand."""
        project_pis_and_managers_data = \
            self.get_project_pis_and_managers_data()
        self.create_project_pis_and_managers(project_pis_and_managers_data)

    def handle_projects_and_project_users(self, *args, **options):
        """Handle the 'projects_and_project_users' subcommand."""
        project_and_project_users_data = \
            self.get_project_and_project_users_data(options['group_file'])
        self.create_projects_and_project_users(project_and_project_users_data)

    def handle_users(self, *args, **options):
        """Handle the 'users' subcommand."""
        user_data = self.get_user_data(options['passwd_file'])
        self.create_users(user_data)

    def create_project_pis_and_managers(self, project_pis_and_managers_data):
        """Create ProjectUsers with role "Principal Investigator" or
        "Manager" given a mapping from project name to a dict
        containing the project's POC names and emails and PI names and
        emails.

        Users who are listed as both PIs and POCs are PIs, and existing
        Users are never demoted to a lower role."""
        pi_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        manager_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')

        for project_name, user_data in project_pis_and_managers_data.items():
            # The Project should already exist.
            try:
                project = Project.objects.get(name=project_name)
            except Project.DoesNotExist:
                self.logger.error(
                    f'Project {project_name} unexpectedly does not exist.')
                continue

            for email, attributes in user_data.items():
                # Create or update User objects.
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    # Users with cluster usernames should already exist, so
                    # this User does not have one. Use their email as their
                    # username.
                    user = User.objects.create(username=email, email=email)
                    self.logger.info(f'User {user.username} was created.')
                except User.MultipleObjectsReturned:
                    self.logger.error(
                        f'Email {email} unexpectedly belongs to multiple '
                        f'users.')
                    continue
                # Prefer existing names (from the cluster) over those from the
                # spreadsheet.
                user.first_name = user.first_name or attributes['first_name']
                user.last_name = user.last_name or attributes['last_name']
                user.save()
                username = user.username

                # Create or update UserProfile objects.
                user_profile, created = UserProfile.objects.update_or_create(
                    user=user)
                if created:
                    self.logger.info(
                        f'UserProfile for User {username} was created.')
                user_profile.middle_name = (
                    user_profile.middle_name or attributes['middle_name'])
                # If the User was already a PI, do not demote them.
                user_profile.is_pi = user_profile.is_pi or attributes['is_pi']
                user_profile.save()

                # Create or update ProjectUser objects.
                role = (
                    pi_project_user_role if attributes['is_pi']
                    else manager_project_user_role)
                try:
                    project_user = ProjectUser.objects.get(
                        user=user, project=project)
                except ProjectUser.DoesNotExist:
                    ProjectUser.objects.create(
                        user=user,
                        project=project,
                        role=role,
                        status=active_project_user_status)
                    self.logger.info(
                        f'ProjectUser ({project_name}, {username}) was '
                        f'created.')
                else:
                    # Only update the role if the ProjectUser didn't already
                    # have the PI role.
                    if project_user.role != pi_project_user_role:
                        project_user.role = role
                    project_user.status = active_project_user_status
                    project_user.save()

    def create_projects_and_project_users(self,
                                          project_and_project_users_data):
        """Create Projects and ProjectUsers given a mapping from project
        name to a set containing the usernames of the users on the
        project."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        user_project_user_role = ProjectUserRoleChoice.objects.get(name='User')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')

        project_defaults = {
            'status': active_project_status,
        }
        project_user_defaults = {
            'role': user_project_user_role,
            'status': active_project_user_status,
        }

        for project_name, usernames in project_and_project_users_data.items():
            project_defaults['title'] = project_name
            project, created = Project.objects.update_or_create(
                name=project_name, defaults=project_defaults)
            if created:
                self.logger.info(f'Project {project_name} was created.')

            for username in usernames:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    self.logger.error(
                        f'Failed to retrieve User {username} when attempting '
                        f'to create a ProjectUser for Project {project_name}.')
                    continue
                project_user, created = ProjectUser.objects.update_or_create(
                    user=user, project=project, defaults=project_user_defaults)
                if created:
                    self.logger.info(
                        f'ProjectUser ({project_name}, {username}) was '
                        f'created.')

    def create_users(self, user_data):
        """Create User objects given a mapping from user username to
        user attributes."""
        for username, attributes in user_data.items():
            user_defaults = {
                'email': attributes['email'].lower(),
                'first_name': attributes['first_name'].title(),
                'last_name': attributes['last_name'].title(),
            }
            user, created = User.objects.update_or_create(
                username=username, defaults=user_defaults)
            if created:
                self.logger.info(f'User {username} was created.')

            user_profile_defaults = {
                'cluster_uid': attributes['cluster_uid'],
                'middle_name': attributes['middle_name'],
            }
            user_profile, created = UserProfile.objects.update_or_create(
                user=user, defaults=user_profile_defaults)
            if created:
                self.logger.info(
                    f'UserProfile for User {username} was created.')

    def get_billing_ids_data(self, billing_file_path):
        """Given a path to a file containing billing IDs, return a
        mapping with two fields:
            1. user_account_fee_ids: A mapping from username to the PID
               to use for the monthly user account fee, and
            2. job_usage_fee_id_users_by_project: A mapping from project
               name to a mapping from PID to usernames of users using
               that PID for the monthly job usage fee under the project.

        Each line in the file is colon-separated and should have eight
        entries. The first is a username, the second is the PID to use
        for the monthly user account fee, and the seventh is a comma-
        separated list of entries of the form 'project_name|PID', where
        the PID is the one to use for the monthly job usage fee.

        The monthly job usage fee is only relevant for Recharge (ac_)
        projects."""
        user_account_fee_ids = {}
        # {project_name: {pid: set_of_usernames_using_pid_for_job_usage}}
        job_usage_fee_id_users_by_project = defaultdict(
            lambda: defaultdict(set))

        with open(billing_file_path, 'r') as billing_file:
            for line in billing_file:
                fields = [
                    field.strip() for field in line.rstrip().split(':')]
                if len(fields) != 8:
                    self.logger.error(
                        f'The entry {fields} does not have 8 fields.')
                    continue
                user_username = fields[0].strip()
                if not user_username:
                    self.logger.error(
                        f'The entry {fields} is missing a username.')
                    continue

                user_account_fee_pid = fields[1].strip()
                job_usage_fee_pids = {}
                for pair in fields[7].strip().split(','):
                    project_name, pid = [s.strip() for s in pair.split('|')]
                    job_usage_fee_pids[project_name] = pid

                all_pids = set.union(
                    {user_account_fee_pid},
                    set(job_usage_fee_pids.values()))
                all_pids_well_formed = all(
                    self.is_billing_id_well_formed(pid) for pid in all_pids)
                if not all_pids_well_formed:
                    self.logger.error(
                        f'The entry {fields} has one or more malformed PIDs.')
                    continue

                user_account_fee_ids[user_username] = user_account_fee_pid
                for project_name, pid in job_usage_fee_pids.items():
                    job_usage_fee_id_users_by_project[project_name][pid].add(
                        user_username)

        return {
            'user_account_fee_ids': user_account_fee_ids,
            'job_usage_fee_id_users_by_project': (
                job_usage_fee_id_users_by_project),
        }

    @staticmethod
    def get_departmental_cluster_names():
        """Return the set of all departmental (non-Lawrencium) cluster
        names, in lowercase."""
        all_names = set(
            [name.lower() for name in get_compute_resource_names()])
        all_names.discard('lawrencium')
        return all_names

    @staticmethod
    def get_first_middle_last_names(full_name):
        """Return the given full name split into first, middle, and last
        in a dictionary."""
        names = {'first': '', 'middle': '', 'last': ''}
        full_name = full_name.strip().split()
        if not full_name:
            return names
        names['first'] = full_name[0]
        if len(full_name) == 2:
            names['last'] = full_name[-1]
        else:
            names['middle'] = ' '.join(full_name[1:-1])
            names['last'] = full_name[-1]
        return names

    def get_project_pis_and_managers_data(self):
        """Given a pre-defined spreadsheet containing the PIs and POCs
        of Projects, return a mapping from a project's name to a dict
        containing the project's POC names and emails and PI names and
        emails."""
        spreadsheet_id = '14YeWGBHYK-9fQ1QtxKzRhyqoPqJlvOZWD8VHocpBX50'
        spreadsheet_tab = 'New-Additions'
        spreadsheet_cols = {
            'NAME': 1,
            'POC_NAMES': 6,
            'POC_EMAILS': 7,
            'PI_NAMES': 8,
            'PI_EMAILS': 9,
        }
        spreadsheet_row_start = 2

        worksheet = get_gspread_worksheet(
            settings.GOOGLE_OAUTH2_KEY_FILE, spreadsheet_id, spreadsheet_tab)
        row_start = spreadsheet_row_start
        row_end = len(worksheet.col_values(spreadsheet_cols['NAME']))
        col_start = 1
        col_end = spreadsheet_cols['PI_EMAILS']
        worksheet_data = get_gspread_worksheet_data(
            worksheet, row_start, row_end, col_start, col_end)

        departmental_cluster_names = self.get_departmental_cluster_names()

        project_pis_and_managers_data = {}
        for row in worksheet_data:
            project_name = row[spreadsheet_cols['NAME'] - 1].strip()
            poc_names = row[spreadsheet_cols['POC_NAMES'] - 1].strip()
            poc_emails = row[spreadsheet_cols['POC_EMAILS'] - 1].strip()
            pi_names = row[spreadsheet_cols['PI_NAMES'] - 1].strip()
            pi_emails = row[spreadsheet_cols['PI_EMAILS'] - 1].strip()
            row_dict = {}

            if not self.is_project_name_valid(
                    project_name, departmental_cluster_names):
                self.logger.info(f'Skipping Project {project_name}.')
                continue

            poc_names = [
                poc_name.strip().title()
                for poc_name in poc_names.split(',')
                if poc_name.strip()]
            if not poc_names:
                self.logger.error(f'Row {row} has no POC names.')
                continue
            poc_names_valid = True
            for full_name in poc_names:
                if not self.is_full_name_valid(full_name):
                    poc_names_valid = False
                    break
            if not poc_names_valid:
                self.logger.error(f'Row {row} has an invalid POC name.')
                continue

            poc_emails = [
                poc_email.strip().lower()
                for poc_email in poc_emails.split(',')
                if poc_email.strip()]
            if not poc_emails:
                self.logger.error(f'Row {row} has no POC emails.')
                continue
            poc_emails_valid = True
            for email in poc_emails:
                if not self.is_email_address_valid(email):
                    poc_emails_valid = False
                    break
            if not poc_emails_valid:
                self.logger.error(f'Row {row} has an invalid POC email.')
                continue
            if len(poc_emails) != len(poc_names):
                self.logger.error(
                    f'Row {row} has {len(poc_names)} POC names, but '
                    f'{len(poc_emails)} POC emails.')
                continue

            for i in range(len(poc_emails)):
                email, full_name = poc_emails[i], poc_names[i]
                names = self.get_first_middle_last_names(full_name)
                user_data = row_dict.get(email, {})
                user_data['first_name'] = names['first']
                user_data['middle_name'] = names['middle']
                user_data['last_name'] = names['last']
                user_data['is_pi'] = False
                row_dict[email] = user_data

            pi_names = [
                pi_name.strip().title()
                for pi_name in pi_names.split(',')
                if pi_name.strip()]
            if not pi_names:
                self.logger.error(f'Row {row} has no PI names.')
                continue
            pi_names_valid = True
            for full_name in pi_names:
                if not self.is_full_name_valid(full_name):
                    pi_names_valid = False
                    break
            if not pi_names_valid:
                self.logger.error(f'Row {row} has an invalid PI name.')
                continue

            pi_emails = [
                pi_email.strip().lower()
                for pi_email in pi_emails.split(',')
                if pi_email.strip()]
            if not pi_emails:
                self.logger.error(f'Row {row} has no PI emails.')
                continue
            pi_emails_valid = True
            for email in pi_emails:
                if not self.is_email_address_valid(email):
                    pi_emails_valid = False
                    break
            if not pi_emails_valid:
                self.logger.error(f'Row {row} has an invalid PI email.')
                continue
            if len(pi_emails) != len(pi_names):
                self.logger.error(
                    f'Row {row} has {len(pi_names)} PI names, but '
                    f'{len(pi_emails)} PI emails.')
                continue

            for i in range(len(pi_emails)):
                email, full_name = pi_emails[i], pi_names[i]
                names = self.get_first_middle_last_names(full_name)
                user_data = row_dict.get(email, {})
                user_data['first_name'] = names['first']
                user_data['middle_name'] = names['middle']
                user_data['last_name'] = names['last']
                user_data['is_pi'] = True
                row_dict[email] = user_data

            project_pis_and_managers_data[project_name] = row_dict

        return project_pis_and_managers_data

    def get_project_and_project_users_data(self, group_file_path):
        """Given a path to the cluster group file, return a mapping from
        a project's name to a set containing the usernames of the users
        on the project."""
        departmental_cluster_names = self.get_departmental_cluster_names()
        project_and_project_users_data = {}
        with open(group_file_path, 'r') as group_file:
            for line in group_file:
                fields = [
                    field.strip() for field in line.rstrip().split(':')]
                if len(fields) != 4:
                    self.logger.error(
                        f'The group {fields} does not have 4 fields.')
                    continue
                project_name = fields[0].strip().lower()
                if not self.is_project_name_valid(
                        project_name, departmental_cluster_names):
                    self.logger.debug(f'Skipping group {project_name}.')
                    continue
                usernames = set([
                    u.strip().lower() for u in fields[3].split(',')
                    if u.strip()])
                project_and_project_users_data[project_name] = usernames
        return project_and_project_users_data

    def get_user_data(self, passwd_file_path):
        """Given a path to the cluster passwd file, return a mapping
        from a user's username to a dict containing the user's
        first_name, middle_name, last_name, cluster_uid, and email."""
        user_data = {}
        with open(passwd_file_path, 'r') as passwd_file:
            for line in passwd_file:
                fields = [
                    field.strip() for field in line.rstrip().split(':')]
                if len(fields) != 7:
                    self.logger.error(
                        f'The user {fields} does not have 7 fields.')
                    continue
                user_username = fields[0].strip()
                if not user_username:
                    self.logger.error(
                        f'The user {fields} is missing a username.')
                    continue
                try:
                    user_id = int(fields[2].strip())
                    if user_id < 0:
                        raise ValueError(
                            f'The user_id {user_id} is invalid.')
                except (TypeError, ValueError):
                    self.logger.error(
                        f'The user {fields} has an invalid user ID: '
                        f'{user_id}.')
                    continue
                full_name_and_email = fields[4].strip()
                if full_name_and_email.count(',') != 1:
                    self.logger.error(
                        f'The user {fields} has a malformed full name and '
                        f'email pair.')
                    continue
                full_name, user_email = full_name_and_email.split(',')
                if not self.is_full_name_valid(full_name):
                    self.logger.error(
                        f'The user {fields} has a malformed full name.')
                    continue
                names = self.get_first_middle_last_names(full_name)
                if not self.is_email_address_valid(user_email):
                    self.logger.error(
                        f'The user {fields} has an invalid email address.')
                    continue
                user_data[user_username] = {
                    'first_name': names['first'],
                    'middle_name': names['middle'],
                    'last_name': names['last'],
                    'cluster_uid': user_id,
                    'email': user_email,
                }
        return user_data

    @staticmethod
    def is_billing_id_well_formed(billing_id):
        """Return whether the given string is a valid billing ID."""
        return bool(re.match('\d{6}-\d{3}', billing_id))

    @staticmethod
    def is_email_address_valid(email):
        """Return whether the given email address is valid."""
        try:
            validate_email(email)
        except ValidationError:
            return False
        return True

    @staticmethod
    def is_full_name_valid(full_name):
        """Return whether the given full name is valid (i.e., it has at
        least two parts)."""
        return len(full_name.split()) >= 2

    @staticmethod
    def is_project_name_valid(project_name, departmental_cluster_names):
        """Return whether the given project name is valid (i.e., it
        begins with a Lawrencium prefix or has the same name as a
        departmental cluster)."""
        project_name = project_name.lower()
        return (
            project_name.startswith(LAWRENCIUM_PROJECT_PREFIXES) or
            project_name in departmental_cluster_names)

    def set_up_departmental_project_allocations(self,
                                                usernames_by_project_name):
        """Set up Allocations for Projects corresponding to the
        departmental clusters.

        For Users who are in the corresponding Project on the cluster,
        set the 'Cluster Account Status' attribute to 'Active'.

        Do not set Service Units, since they are not relevant."""
        start_date = utc_now_offset_aware()
        allocation_kwargs = {
            'start_date': start_date,
            'end_date': None,
            'num_service_units': None,
        }
        allocation_user_kwargs = {
            'num_service_units': None,
        }

        departmental_cluster_names = self.get_departmental_cluster_names()

        for project in Project.objects.filter(
                name__in=departmental_cluster_names):
            resource = Resource.objects.get(
                name=f'{project.name.upper()} Compute')
            allocation = self.set_up_project_allocation_to_compute_resource(
                project, resource, **allocation_kwargs)

            project_users = ProjectUser.objects.prefetch_related(
                'status', 'user__userprofile').filter(
                    project=project, status__name='Active')
            for project_user in project_users:
                allocation_user_kwargs['has_project_access_on_cluster'] = (
                    project_user.user.username in usernames_by_project_name)
                self.set_up_project_allocation_user(
                    project_user, allocation, **allocation_user_kwargs)

    def set_up_lawrencium_project_allocations(self, usernames_by_project_name):
        """Set up Allocations for Projects corresponding to the
        Lawrencium cluster.

        For Users who are in the corresponding Project on the cluster,
        set the 'Cluster Account Status' attribute to 'Active'.

        Set Service Units:
            - Condo projects receive the maximum amount, since they have
            no limits.
            - PCA projects receive 0, since they will be renewed later.
            - Recharge projects receive the maximum amount, since they
            are charged monthly for however much they use."""
        start_date = utc_now_offset_aware()
        allocation_kwargs = {
            'start_date': start_date,
            'end_date': None,
            'num_service_units': None,
        }
        allocation_user_kwargs = {
            'num_service_units': None,
        }

        resource = Resource.objects.get(name='LAWRENCIUM Compute')

        for project in Project.objects.all():
            if project.name.startswith('ac_'):
                end_date = None
                num_service_units = settings.ALLOCATION_MAX
            elif project.name.startswith('lr_'):
                end_date = None
                num_service_units = settings.ALLOCATION_MAX
            elif project.name.startswith('pc_'):
                end_date = (
                    next_allocation_start_datetime() - timedelta(seconds=1))
                num_service_units = settings.ALLOCATION_MIN
            else:
                continue
            allocation_kwargs['end_date'] = end_date
            allocation_kwargs['num_service_units'] = num_service_units
            allocation_user_kwargs['num_service_units'] = num_service_units

            allocation = self.set_up_project_allocation_to_compute_resource(
                project, resource, **allocation_kwargs)

            project_users = ProjectUser.objects.prefetch_related(
                'status', 'user__userprofile').filter(
                    project=project, status__name='Active')
            for project_user in project_users:
                allocation_user_kwargs['has_project_access_on_cluster'] = (
                    project_user.user.username in usernames_by_project_name)
                self.set_up_project_allocation_user(
                    project_user, allocation, **allocation_user_kwargs)

    def set_up_project_allocation_to_compute_resource(self, project, resource,
                                                      start_date=None,
                                                      end_date=None,
                                                      num_service_units=None):
        """Create an Allocation to the given Compute resource for the
        given Project, set its start and end dates, and optionally set
        its service units to the given value. Return the created
        Allocation.

        If num_service_units is not a Decimal, skip creation of
        "Service Units"-related database objects."""
        active_allocation_status = AllocationStatusChoice.objects.get(
            name='Active')
        allocation_defaults = {
            'status': active_allocation_status,
            'start_date': start_date,
            'end_date': end_date,
        }

        allocation, created = Allocation.objects.update_or_create(
            project=project, defaults=allocation_defaults)
        allocation.resources.add(resource)
        if created:
            self.logger.info(
                f'Allocation {allocation.pk} to Resource {resource.name} for '
                f'Project {project.name} was created.')

        if not isinstance(num_service_units, Decimal):
            return allocation

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute_defaults = {
            'value': str(num_service_units),
        }
        allocation_attribute, _ = AllocationAttribute.objects.update_or_create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation, defaults=allocation_attribute_defaults)

        ProjectTransaction.objects.create(
            project=project,
            date_time=utc_now_offset_aware(),
            allocation=num_service_units)

        # A usage should have been created for the attribute.
        try:
            AllocationAttributeUsage.objects.get(
                allocation_attribute=allocation_attribute)
        except AllocationAttributeUsage.DoesNotExist:
            raise AllocationAttributeUsage.DoesNotExist(
                f'Unexpected: No AllocationAttributeUsage object exists for'
                f'AllocationAttribute {allocation_attribute.pk}.')

        return allocation

    @staticmethod
    def set_up_project_allocation_user(project_user, allocation,
                                       has_project_access_on_cluster=False,
                                       num_service_units=None):
        """Create an AllocationUser under the given Allocation for the
        given ProjectUser, activate its cluster account status if
        appropriate, and optionally set its service units to the given
        value. Return the created AllocationUser.

        If num_service_units is not a Decimal, skip creation of
        "Service Units"-related database objects."""
        user = project_user.user
        allocation_user = get_or_create_active_allocation_user(
            allocation, user)

        if has_project_access_on_cluster:
            set_allocation_user_attribute_value(
                allocation_user, 'Cluster Account Status', 'Active')
        allocation_user.refresh_from_db()

        if not isinstance(num_service_units, Decimal):
            return allocation_user

        allocation_user_attribute = set_allocation_user_attribute_value(
            allocation_user, 'Service Units', str(num_service_units))
        allocation_user.refresh_from_db()

        ProjectUserTransaction.objects.create(
            project_user=project_user,
            date_time=utc_now_offset_aware(),
            allocation=num_service_units)

        # A usage should have been created for the attribute.
        try:
            AllocationUserAttributeUsage.objects.get(
                allocation_user_attribute=allocation_user_attribute)
        except AllocationUserAttributeUsage.DoesNotExist:
            raise AllocationUserAttributeUsage.DoesNotExist(
                f'Unexpected: No AllocationUserAttributeUsage object '
                f'exists for AllocationUserAttribute '
                f'{allocation_user_attribute.pk}.')

        return allocation_user
