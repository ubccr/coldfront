from dateutil import parser as date_parser
from decimal import Decimal
from decimal import InvalidOperation
import json
import logging
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.module_loading import import_string

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.project.utils_.renewal_utils import has_non_denied_renewal_request
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.common import validate_num_service_units
from coldfront.core.utils.email.email_strategy import DropEmailStrategy


"""An admin command that loads completed AllocationRenewalRequests from
a JSON file and optionally processes them."""


class Command(BaseCommand):

    help = (
        'Create completed AllocationRenewalRequests from a JSON. Optionally '
        'process them before marking them as completed. WARNING: This is not '
        'a command meant for general use; it is intended to load in requests '
        'from legacy Google Forms, and should not need to be run more than '
        'once. Proceed with caution.')

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.email_module_dict = {}

    def add_arguments(self, parser):
        parser.add_argument(
            'json',
            help=(
                'The path to the JSON file containing a list of objects, '
                'where each object contains the following keys: '
                '"requester_email", "pi_email", "pi_name", '
                '"pre_project_name", "post_project_name", "request_time", '
                '"num_service_units".'),
            type=self.existent_file)
        parser.add_argument(
            'allocation_period_name',
            help='The name of the AllocationPeriod the renewals are under.',
            type=str)
        # TODO: Remove this once all emails are transitioned to
        # TODO: allauth.account.models.EmailAddress.
        parser.add_argument(
            'email_module',
            choices=['allauth.account.models', 'coldfront.core.user.models'],
            help=(
                'There are temporarily two EmailAddress models, until all can '
                'be transitioned under allauth.account.models.'),
            type=str)
        parser.add_argument(
            '--process',
            help=(
                'Run processing on valid requests. If this argument is not '
                'provided, each request will be marked as "Complete" without '
                'performing any of the associated processing tasks (e.g., '
                'activating the project, granting service units, etc.). '
                'Processing performed via this argument does not send email '
                'to users.'))
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        """Process the input JSON. Create requests for valid pairs, or
        display what requests would be created (if dry_run)."""
        file_path = options['json']

        allocation_period_name = options['allocation_period_name']
        try:
            allocation_period = AllocationPeriod.objects.get(
                name=allocation_period_name)
        except AllocationPeriod.DoesNotExist:
            raise CommandError(
                f'Invalid AllocationPeriod {allocation_period_name}.')

        email_module = options['email_module']
        if email_module == 'allauth.account.models':
            verified_field, primary_field = 'verified', 'primary'
        else:
            verified_field, primary_field = 'is_verified', 'is_primary'
        self.email_module_dict['model'] = import_string(
            f'{email_module}.EmailAddress')
        self.email_module_dict['verified_field'] = verified_field
        self.email_module_dict['primary_field'] = primary_field

        valid, already_renewed, invalid = self.parse_input_file(
            file_path, allocation_period)
        self.process_valid_objects(
            valid, allocation_period, options['process'], options['dry_run'])
        self.process_already_renewed_pis(already_renewed, allocation_period)
        self.process_invalid_objects(invalid)

    @staticmethod
    def existent_file(path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'Invalid path {path}.')
        if not os.path.isfile(path):
            raise IsADirectoryError(f'Invalid file {path}.')
        return path

    def parse_input_file(self, file_path, allocation_period):
        """Given a path to a JSON input file and an AllocationPeriod,
        partition the entries into three lists: (1) valid objects with
        the following keys: "requester_email", "pi_email", "pi_name",
        "pre_project", "post_project", "request_time",
        "num_service_units", (2) Users that have already renewed, and
        (3) invalid input objects."""
        with open(file_path, 'r') as f:
            input_dicts = json.load(f)

        valid, already_renewed, invalid = [], [], []

        seen_pi_emails = set()

        for input_dict in input_dicts:
            for key in input_dict:
                input_dict[key] = input_dict[key].strip()
            requester_email = input_dict['requester_email'].lower()
            pi_email = input_dict['pi_email'].lower()
            pi_name = input_dict['pi_name'].lower()
            pre_project_name = input_dict['pre_project_name'].lower()
            post_project_name = input_dict['post_project_name'].lower()
            request_time = input_dict['request_time']
            num_service_units = input_dict['num_service_units']

            # If the PI was the PI of a previous entry, mark this entry as
            # invalid.
            if pi_email in seen_pi_emails:
                invalid.append(input_dict)
                continue
            seen_pi_emails.add(pi_email)

            # Validate that the PI does not already have a non-'Denied'
            # AllocationRenewalRequest for this period.
            pi = self._get_user_with_email(pi_email)
            if (isinstance(pi, User) and
                    has_non_denied_renewal_request(pi, allocation_period)):
                already_renewed.append(pi)
                continue

            # Validate that the pre-Project exists, if given. The PI may have
            # previously not had a Project.
            if not pre_project_name:
                pre_project = None
            else:
                try:
                    pre_project = Project.objects.get(name=pre_project_name)
                except Project.DoesNotExist:
                    invalid.append(input_dict)
                    continue

            # Validate that the post-Project exists.
            try:
                post_project = Project.objects.prefetch_related(
                    'projectuser_set').get(name=post_project_name)
            except ProjectUser.DoesNotExist:
                invalid.append(input_dict)
                continue

            # Validate the ISO 8601 timestamp.
            try:
                request_time = date_parser.isoparse(request_time)
            except ValueError:
                invalid.append(input_dict)
                continue

            # Validate the number of service units.
            try:
                num_service_units = Decimal(num_service_units)
                validate_num_service_units(num_service_units)
            except (InvalidOperation, ValueError):
                invalid.append(input_dict)
                continue

            entry = {
                'requester_email': requester_email,
                'pi_email': pi_email,
                'pi_name': pi_name,
                'pre_project': pre_project,
                'post_project': post_project,
                'request_time': request_time,
                'num_service_units': num_service_units,
            }
            valid.append(entry)

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

    def process_invalid_objects(self, invalid_objects):
        """Given a list of objects, where some entry is invalid, write to
        stderr."""
        for invalid_object in invalid_objects:
            message = f'Invalid object: {invalid_object}. Skipping.'
            self.stderr.write(self.style.ERROR(message))

    def process_valid_objects(self, valid, allocation_period, process,
                              dry_run):
        """Given a list of valid objects, for each object, create an
        AllocationRenewalRequest under the given AllocationPeriod with
        status 'Complete', and write to stdout. Potentially additionally
        update or create User and EmailAddress objects for the requester
        and/or PI.

        If process is True, run processing on requests before marking
        them as completed.

        If dry_run is True, write the details to stdout without creating
        any objects."""
        interface = ComputingAllowanceInterface()
        approved_renewal_status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Approved')
        complete_renewal_status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        for valid_dict in valid:
            requester_email = valid_dict['requester_email']
            pi_email = valid_dict['pi_email']
            pi_name = valid_dict['pi_name']
            pre_project = valid_dict['pre_project']
            post_project = valid_dict['post_project']
            request_time = valid_dict['request_time']
            num_sus = valid_dict['num_service_units']

            requester_str = f'Unnamed Requester ({requester_email})'
            pi_name_parts = self._get_first_middle_last_names(pi_name)
            pi_str = (
                f'{pi_name_parts["first"]} {pi_name_parts["last"]} '
                f'({pi_email})')
            if dry_run:
                message = (
                    f'Would create pre-completed AllocationRenewalRequest for '
                    f'PI {pi_str}, requester {requester_str}, pre-Project '
                    f'{pre_project.name}, post-Project {post_project.name}, '
                    f'and AllocationPeriod {allocation_period.name}, with '
                    f'request_time {request_time} and {num_sus} service '
                    f'units.')
                self.stdout.write(self.style.WARNING(message))
                continue

            try:
                with transaction.atomic():
                    # Update or create User and EmailAddress objects for the
                    # requester and PI, who may be the same.
                    requester_user = \
                        self._update_or_create_user_and_email_address(
                            requester_email)
                    requester_str = (
                        f'{requester_user.first_name} '
                        f'{requester_user.last_name} ({requester_user.email})')
                    pi_name_parts = self._get_first_middle_last_names(pi_name)
                    pi_user = self._update_or_create_user_and_email_address(
                        pi_email, first_name=pi_name_parts['first'],
                        middle_name=pi_name_parts['middle'],
                        last_name=pi_name_parts['last'], set_is_pi=True)
                    pi_str = (
                        f'{pi_user.first_name} {pi_user.last_name} '
                        f'({pi_user.email})')
                    requester_user.refresh_from_db()

                    # Create the request.
                    now = utc_now_offset_aware()
                    request_kwargs = {
                        'requester': requester_user,
                        'pi': pi_user,
                        'computing_allowance': interface.allowance_from_code(
                            post_project.name[:3]),
                        'allocation_period': allocation_period,
                        'pre_project': pre_project,
                        'post_project': post_project,
                        'num_service_units': num_sus,
                        'request_time': request_time,
                        'approval_time': now,
                    }
                    if process:
                        request_kwargs['status'] = approved_renewal_status
                    else:
                        request_kwargs['status'] = complete_renewal_status
                    request = AllocationRenewalRequest.objects.create(
                        **request_kwargs)
                    request.state['eligibility']['status'] = 'Approved'
                    request.state['eligibility']['timestamp'] = now.isoformat()
                    request.save()

                    # Optionally performing processing for the request.
                    if process:
                        runner = AllocationRenewalProcessingRunner(
                            request, request.num_service_units,
                            email_strategy=DropEmailStrategy())
                        runner.run()
                    else:
                        request.completion_time = now
                        request.save()
            except Exception as e:
                message = (
                    f'Failed to create AllocationRenewalRequest for PI '
                    f'{pi_str}, requester {requester_str}, pre-Project '
                    f'{pre_project.name}, and post-Project '
                    f'{post_project.name}.')
                self.stderr.write(self.style.ERROR(message))
                self.logger.exception(e)
            else:
                message = (
                    f'Created pre-completed AllocationRenewalRequest '
                    f'{request.pk} for PI {pi_str}, requester '
                    f'{requester_str}, pre-Project {pre_project.name}, '
                    f'post-Project {post_project.name}, and AllocationPeriod '
                    f'{allocation_period.name}, with request_time '
                    f'{request_time} and {num_sus} service units.')
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))

    def _update_or_create_user_and_email_address(self, email, first_name='',
                                                 middle_name='', last_name='',
                                                 set_is_pi=False):
        """Ensure that a User and an EmailAddress exist for the given
        email. If provided (and not already set), set the given first,
        middle, and last names. Also update UserProfile.is_pi if
        requested."""
        EmailAddress = self.email_module_dict['model']
        email_verified_field = self.email_module_dict['verified_field']
        email_primary_field = self.email_module_dict['primary_field']

        user = self._get_user_with_email(email)
        if isinstance(user, User):
            user.first_name = user.first_name or first_name
            user.last_name = user.last_name or last_name

            user_profile = user.userprofile
            user_profile.middle_name = user_profile.middle_name or middle_name
            if set_is_pi:
                user_profile.is_pi = True

            with transaction.atomic():
                user.save()
                user_profile.save()
                email_address, created = EmailAddress.objects.update_or_create(
                    user=user,
                    email=email,
                    defaults={
                        email_verified_field: True,
                        email_primary_field: True})
            if created:
                message = (
                    f'Created EmailAddress {email_address.pk} for User '
                    f'{user.pk} and address {email}.')
                self.logger.info(message)
        else:
            with transaction.atomic():
                user = User.objects.create(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name)
                user_profile = user.userprofile
                user_profile.middle_name = middle_name
                if set_is_pi:
                    user_profile.is_pi = True
                user_profile.save()
                kwargs = {
                    'user': user,
                    'email': email,
                    email_verified_field: True,
                    email_primary_field: True,
                }
                email_address = EmailAddress.objects.create(**kwargs)
            message = (
                f'Created User {user.pk} and associated EmailAddress '
                f'{email_address.pk} for address {email}.')
            self.logger.info(message)
        return user

    @staticmethod
    def _get_first_middle_last_names(full_name):
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

    def _get_user_with_email(self, email):
        """Return the User associated with the given email, or None."""
        EmailAddress = self.email_module_dict['model']
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            pass
        try:
            return EmailAddress.objects.get(email__iexact=email).user
        except EmailAddress.DoesNotExist:
            pass
        return None
