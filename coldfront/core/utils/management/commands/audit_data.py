'''
Add a command audit_data to ensure that certain invariants hold. These include,
but are not limited to:
 - Allocations have the expected start_date and end_date values.
 - Inactive Projects have "Expired" Allocations and zero SUs.
 - Each Project has at least one PI.
 - Users with a cluster UID should be associated with at least one Project.
TODO: Lawrencium features don't work and need to be further developed.
LRC only:
 - Each UserProfile with access to Lawrencium should have a billing_activity.
 - Each Recharge Allocation that has access to Lawrencium should have a
    "Billing Activity"-typed AllocationAttribute.
 - Each Recharge AllocationUser that has access to Lawrencium should have a
    "Billing Activity"-typed AllocationUserAttribute.
 - From Enforce that LRC PIs are LBL employees #392, each PI of a Project on
    Lawrencium must be an LBL employee.

'''

import datetime
from flags.state import flag_enabled

from django.core.management.base import BaseCommand
from django.db.models import Q

from coldfront.core.allocation.models import Allocation, \
                                             AllocationPeriod, \
                                             AllocationUser
from coldfront.core.project.models import Project, \
                                          ProjectUser
from coldfront.core.user.models import UserProfile
from coldfront.core.allocation.models import AllocationAttribute

from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date

class Command(BaseCommand):
    help = 'Audit data to ensure that certain invariants hold.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
            help='Run all non-LRC-only checks')
        parser.add_argument('--allocation-date', action='store_true',
            help='Check that allocations have the expected start_date and '
            'end_date values')
        parser.add_argument('--project-inactive', action='store_true',
            help='Check that inactive projects have "Expired" allocations and '
            'zero SUs')
        parser.add_argument('--project-pi', action='store_true',
            help='Check that projects have at least one PI')
        parser.add_argument('--user-project', action='store_true',
            help='Check that users with a cluster UID should be associated '
            'with at least one Project')

        parser.add_argument('--lrc-user-billing', action='store_true',
            help='Check that LRC users have a billing_activity')
        parser.add_argument('--lrc-recharge-allocation-billing',
                action='store_true',
                help='Check that LRC Recharge Allocations have a '
                '"Billing Activity"-typed AllocationAttribute')
        parser.add_argument('--lrc-recharge-allocation-user-billing',
            action='store_true',
            help='Check that LRC Recharge AllocationUsers have a '
            '"Billing Activity"-typed AllocationUserAttribute')
        parser.add_argument('--lrc-pis-lbl-employee', action='store_true',
            help='Check that LRC PIs are LBL employees')


    def handle(self, *args, **options):
        if options['all']:
            options['allocation_date'] = True
            options['project_inactive'] = True
            options['project_pi'] = True
            options['user_project'] = True
            # TODO: Uncomment when Lawrencium features are ready.
            # options['lrc_all'] = flag_enabled('LRC_ONLY')
        if options.get('lrc_all', False):
            options['lrc_user_billing'] = True
            options['lrc_recharge_allocation_billing'] = True
            options['lrc_recharge_allocation_user_billing'] = True
            options['lrc_pis_lbl_employee'] = True
        for option in options:
            if isinstance(options[option], bool) and options[option] and \
                    option not in ('all', 'lrc_all'):
                self.stdout.write(self.style.SUCCESS(f'Running {option}...'))
                getattr(self, f'handle_{option}')()
                self.stdout.write(self.style.SUCCESS('Audit complete.') + '\n\n')

    def handle_allocation_date(self):
        '''
        Assert that all compute allocations have the expected start_date
        and end_date values.
        - Allocation end date is after the start date
        - FCAs and PCAs:
          FCAs and PCAs are valid within a so-called “Allowance Year”
          (June 1st - May 31st for BRC, October 1st - September 30th for LRC):
            - Inactive ones (ones that were not renewed) should have a start
                date set to the start of the current allowance year
                AllocationPeriod, but no end date.
            - Active ones (ones that were renewed, or were created during
                this allowance year) should have the same start and end date as
                the current allowance year AllocationPeriod.
          ICAs (Instructional Computing Allowances) are valid within a
          particular UC Berkeley semester.
            - Inactive ones should have a start date, but no end date.
            - Active ones (currently none on production) should match a current
                (has started, but has not ended) instructional AllocationPeriod.
          Recharge and Condo may/should have start dates, but don’t have end
          dates, as they don’t end.
        '''
        allocations = Allocation.objects.select_related('project',
                            'project__status').prefetch_related('resources') \
            .filter(resources__name__endswith='Compute') \
            .order_by('resources__name', 'project__name',
                      'project__status__name', 'start_date', 'end_date') \
            .values('id', 'project__status__name',
                   'project__name','start_date', 'end_date',
                   'resources__name')

        FCA_PCA_ALLOCATION_PERIOD = get_current_allowance_year_period()
        ICA_ALLOCATION_PERIODS = AllocationPeriod.objects.filter(
                                    Q(end_date__gt=display_time_zone_current_date())
                                    & (Q(name__startswith='Fall Semester')
                                       | Q(name__startswith='Spring Semester')
                                       | Q(name__startswith='Summer Sessions') \
                                      )).all()

        FCA_PCA_PREFIXES = ('fc_', 'pc_')
        ICA_PREFIX = 'ic_'
        RECHARGE_CONDO_PREFIX = ('co_', 'ac_')

        for allocation in allocations:
            id = allocation['id']
            start_date = allocation['start_date']
            end_date = allocation['end_date']
            project_status = allocation['project__status__name']
            project = allocation['project__name']
            resource = allocation['resources__name']

            if end_date is not None and end_date < start_date:
                self.stdout.write(self.style.ERROR(f'{resource} {id} '
                f'for {project_status.lower()} project {project} has an end '
                f'date before its start date.'))

            if project.startswith(FCA_PCA_PREFIXES):
                if project_status == 'Inactive' \
                        and start_date != FCA_PCA_ALLOCATION_PERIOD.start_date:
                    self.stdout.write(self.style.ERROR(f'{resource} {id} '
                    f'for inactive FCA or PCA project {project} has a start '
                    f'date of {start_date} that is different than its '
                    f'allocation period\'s '
                    f'({FCA_PCA_ALLOCATION_PERIOD.start_date} for '
                    f'{FCA_PCA_ALLOCATION_PERIOD}).'))
                if project_status == 'Active':
                    if start_date < FCA_PCA_ALLOCATION_PERIOD.start_date:
                        self.stdout.write(self.style.ERROR(f'{resource} {id} '
                        f'for active FCA or PCA project {project} has a '
                        f'start date of {start_date} that is before '
                        f'its allocation period\'s '
                        f'({FCA_PCA_ALLOCATION_PERIOD.start_date} for '
                        f'{FCA_PCA_ALLOCATION_PERIOD}).'))
                    if end_date != FCA_PCA_ALLOCATION_PERIOD.end_date:
                        self.stdout.write(self.style.ERROR(f'{resource} {id} '
                        f'for active FCA or PCA project {project} has an end '
                        f'date of {end_date} that is different than '
                        f'its allocation period\'s '
                        f'({FCA_PCA_ALLOCATION_PERIOD.end_date} for '
                        f'{FCA_PCA_ALLOCATION_PERIOD}).'))

            elif project.startswith(ICA_PREFIX):
                if project_status == 'Inactive' and end_date is not None:
                    self.stdout.write(self.style.ERROR(f'{resource} {id} '
                    f'for inactive ICA project {project} has an end date '
                    f'(it shouldn\'t as it\'s inactive).'))
                if project_status == 'Active' \
                        and not any(end_date != ica.end_date \
                            for ica in ICA_ALLOCATION_PERIODS):
                    self.stdout.write(self.style.ERROR(f'{resource} {id} '
                    f'for {project_status.lower()} ICA project '
                    f'{project} has an end date that is different from all ICA '
                    f'allocation periods.'))
            elif project.startswith(RECHARGE_CONDO_PREFIX):
                if end_date is not None:
                    self.stdout.write(self.style.ERROR(f'{resource} {id} '
                    f'for {project_status.lower()} Recharge or Condo '
                    f'allocation project {project} has an end date. '
                    f'(it shouldn\'t)'))

    def handle_project_inactive(self):
        '''
        Assert that inactive Projects have "Expired" allocations and zero SUs.
        '''
        inactive_projects = Project.objects \
                                .prefetch_related('allocation_set__status',
                                    'allocation_set__resources',
                                    'allocation_set__allocationattribute_set') \
                                .filter(status__name='Inactive') \
                                .order_by('name')

        for project in inactive_projects:
            for allocation in project.allocation_set \
                              .select_related('status') \
                              .prefetch_related('allocationattribute_set',
                                                'resources'):
                try:
                    resource = allocation.resources.first().name
                    style = (lambda x:
                            self.style.WARNING('CURRENTLY EXPECTED BEHAVIOR: ') \
                            + self.style.WARNING(x)) if \
                            resource.endswith('Directory') \
                            else self.style.ERROR
                    if allocation.status.name != 'Expired':
                        self.stdout.write(style(f'Project {project.name} is '
                        f'inactive and has an unexpired '
                        f'{resource} allocation {allocation.id}.'))
                except AttributeError as e:
                    pass
                try:
                    allocation_attribute = allocation.allocationattribute_set \
                        .get(allocation_attribute_type__name='Service Units')
                    if allocation_attribute.value != '0' and \
                       allocation_attribute.value != '0.00':
                        self.stdout.write(self.style.ERROR(
                        f'Project {project.name} is inactive and has '
                        f'non-zero SUs.'))
                except AllocationAttribute.DoesNotExist as e:
                    pass

    def handle_project_pi(self):
        '''
        Assert that all projects have at least one PI.
        '''
        projects = Project.objects \
            .select_related('status') \
            .order_by('status__name', 'name')
        for project in projects:
            if not project.pis().exists():
                self.stdout.write(self.style.ERROR( f'{project.status.name} '
                f'Project {project.name} has no PIs.'))

    def handle_user_project(self):
        '''
        Assert that all users with a cluster UID should be associated with
        at least one Project.
        '''
        users = UserProfile.objects.filter(cluster_uid__isnull=False) \
            .select_related('user') \
            .order_by('user__is_active', 'user__username') \
            .values('id', 'user__first_name', 'user__last_name',
                    'user__email', 'user__username', 'user__is_active')

        for user in users:
            user_project_exists = ProjectUser.objects \
                .filter(user_id=user['id']).exists()
            if not user_project_exists:
                self.stdout.write(self.style.ERROR(
                f'{("Inactive", "Active")[user["user__is_active"]]} User '
                f'{user["user__username"]} ({user["user__first_name"]} '
                f'{user["user__last_name"]}, {user["user__email"]}) '
                f'has a cluster UID but is not associated with any projects.'))

    def handle_lrc_user_billing(self):
        '''
        TODO: Lawrencium features don't work and need to be further developed.
        Assert that all LRC users have a billing_activity.
        '''
        users = UserProfile.objects.filter(cluster_uid__isnull=False) \
            .values('id', 'billing_activity', 'user__first_name',
                    'user__last_name', 'user__email')
        for user in users:
            if user['billing_activity'] is None:
                self.stdout.write(self.style.ERROR(
                f'{("Inactive", "Active")[user["user__is_active"]]} User '
                f'{user["user__username"]} ({user["user__first_name"]} '
                f'{user["user__last_name"]}, {user["user__email"]}) '
                f'has a cluster UID but is not associated with any billing '
                f'activity.'))

    def handle_lrc_recharge_allocation_billing(self):
        '''
        TODO: Lawrencium features don't work and need to be further developed.
        Assert that all LRC Recharge Allocations have a "Billing Activity"-typed
         AllocationAttribute.
        '''
        allocations = Allocation.objects \
            .prefetch_related('resources') \
            .filter(resources__name__endswith='Compute')
        for allocation in allocations:
            if allocation.allocationattribute_set \
                    .filter(type='Billing Activity').count() == 0:
                self.stdout.write(self.style.ERROR(
                f'{allocation.resources.name} Allocation {allocation.id}'
                f' has no "Billing Activity"-typed AllocationAttribute.'))

    def handle_lrc_recharge_allocation_user_billing(self):
        '''
        TODO: Lawrencium features don't work and need to be further developed.
        Assert that all LRC Recharge AllocationUsers have a
        "Billing Activity"-typed AllocationUserAttribute.
        '''
        allocation_users = AllocationUser.objects \
            .filter(allocation_resources__name__endswith='Compute')
        for allocation_user in allocation_users:
            if allocation_user.allocationuserattribute_set.filter(
                    type='Billing Activity').count() == 0:
                self.stdout.write(self.style.ERROR(
                    f'AllocationUser {allocation_user.id} '
                    f'({allocation_user.user.first_name} '
                    f'{allocation_user.user.last_name}, '
                    f'{allocation_user.user.email}) '
                    'has no "Billing Activity"-typed AllocationUserAttribute.'))

    def handle_lrc_pis_lbl_employee(self):
        '''
        TODO: Lawrencium features don't work and need to be further developed.
        Assert that all LRC PIs are LBL employees.
        '''
        pis = UserProfile.objects.filter(cluster_uid__isnull=False, is_pi=True)
        for pi in pis:
            if not pi.is_lbl_employee():
                self.stdout.write(self.style.ERROR(
                f'User {pi.id} ({pi.user.first_name} {pi.user.last_name}, '
                f'{pi.user.email}) is not an LBL employee.'))