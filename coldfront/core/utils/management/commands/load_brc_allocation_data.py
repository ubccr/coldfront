from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils import get_project_compute_resource_name
from coldfront.core.resource.models import Resource
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet_data
from decimal import Decimal
from decimal import InvalidOperation
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand
import logging

"""An admin command that loads allocation data for BRC."""


# Settings for the 'Savio-Projects' spreadsheet.
SPREADSHEET_ID = '10Dby-MPDkWIovGkqWTS6MEYMofOKm4Ng5o7Zd5TrI2U'
SPREADSHEET_TABS = {
    'fc_': 'FCA-Projects',
    'pc_': 'Partner-Projects',
    'ic_': 'ICA-Projects',
    'co_': 'Condo-Projects',
    'ac_': 'MOU-Projects',
}
SPREADSHEET_ROW_START = 2
SPREADSHEET_COLS = {
    'NAME': 2,
    'ALLOCATION': 5,
}


class Command(BaseCommand):

    help = 'Loads allocation data from a BRC spreadsheet.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # Retrieve data from the spreadsheet.
        allocations = self.get_allocation_data()
        # Filter out and log invalid allocation entries.
        valid_allocations = self.get_valid_allocations(allocations)
        # Update database objects.
        for name, value in valid_allocations.items():
            # Set allocations for the Project and its users.
            try:
                project = Project.objects.get(name=name)
            except Project.DoesNotExist:
                raise Project.DoesNotExist(
                    f'Project {name} unexpectedly does not exist.')
            self.set_allocations(project, value)
        # Create allocations for active Vector projects.
        self.create_vector_allocations()
        # Create allocations for the abc project.
        self.create_abc_allocations()

    @staticmethod
    def get_allocation_data():
        """Return a mapping from project name to allocation amount,
        retrieved from the spreadsheet. For FCA, Partner, and ICA
        projects, allocations are set to the values stored in the
        spreadsheet. For Condo and Recharge (MOU) projects, allocations
        are set to None.

        Parameters:
            - None

        Returns:
            - Dictionary mapping project name to allocation value

        Raises:
            - Exception, if any errors occur
        """
        allocation_data = {}
        for prefix in SPREADSHEET_TABS:
            tab = SPREADSHEET_TABS[prefix]
            worksheet = get_gspread_worksheet(
                settings.GOOGLE_OAUTH2_KEY_FILE, SPREADSHEET_ID, tab)
            row_start = SPREADSHEET_ROW_START
            row_end = len(worksheet.col_values(SPREADSHEET_COLS['NAME']))
            col_start = 1
            if prefix in ('fc_', 'pc_', 'ic_', 'ac_'):
                col_end = SPREADSHEET_COLS['ALLOCATION']
            elif prefix == 'co_':
                col_end = SPREADSHEET_COLS['NAME']
            else:
                continue
            data = get_gspread_worksheet_data(
                worksheet, row_start, row_end, col_start, col_end)
            for project in data:
                name = project[SPREADSHEET_COLS['NAME'] - 1].strip()
                if col_end >= SPREADSHEET_COLS['ALLOCATION']:
                    allocation = project[
                        SPREADSHEET_COLS['ALLOCATION'] - 1].strip()
                else:
                    allocation = None
                allocation_data[name] = allocation
        return allocation_data

    def get_valid_allocations(self, allocation_data):
        """Return the subset of the given project allocations for which
        the project exists and the allocation is a valid number within
        the acceptable range.

        Parameters:
            - allocation_data (dict): a dictionary mapping project name
                                      to allocation value

        Returns:
            - Dictionary mapping project name to allocation value

        Raises:
            - None
        """
        valid, invalid = {}, {}
        for name, allocation in allocation_data.items():
            name = name.strip()
            try:
                Project.objects.get(name=name)
            except Project.DoesNotExist:
                invalid[name] = allocation
                continue
            if name.startswith(('fc_', 'pc_', 'ic_', 'ac_')):
                if allocation is None:
                    allocation = '0.00'
                try:
                    allocation = Decimal(allocation)
                except InvalidOperation:
                    invalid[name] = allocation
                    continue
                if (allocation < settings.ALLOCATION_MIN or
                        allocation > settings.ALLOCATION_MAX):
                    invalid[name] = allocation
                    continue
            elif name.startswith('co_'):
                allocation = settings.ALLOCATION_MAX
            else:
                invalid[name] = allocation
                continue
            valid[name] = allocation
        self.logger.info(f'Number of Valid rows: {len(valid)}')
        self.logger.info(f'Number of Invalid rows: {len(invalid)}')
        for name, allocation in invalid.items():
            self.logger.error(f'Invalid row ({name}, {allocation}).')
        return valid

    def set_allocations(self, project, value):
        """Set allocation values for the Savio Compute resource for the
        project and all its users to the given value. Create any
        intermediate objects as needed.

        Parameters:
            - project (Project): a Project instance
            - value (Decimal): the allocation value

        Returns:
            - None

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if a given Project has more than
            allocation to the Savio Compute resource
        """
        # Create or retrieve the project's allocation to the Savio Compute
        # resource, of which there should be only one.
        allocation = self.__get_or_create_allocation(project)

        # Create or retrieve the allocation's Service Units attribute. Set its
        # value.
        allocation_attribute = self.__get_or_create_allocation_attribute(
            allocation, 'Service Units', str(value))

        # A usage object should exist for the allocation attribute.
        try:
            AllocationAttributeUsage.objects.get(
                allocation_attribute=allocation_attribute)
        except AllocationAttributeUsage.DoesNotExist:
            raise AllocationAttributeUsage.DoesNotExist(
                f'Unexpected: No AllocationAttributeUsage object exists for '
                f'AllocationAttribute {allocation_attribute.pk}.')

        # Set allocations and cluster account statuses for each of the
        # project's users.
        project_users = ProjectUser.objects.prefetch_related(
            'status', 'user__userprofile'
        ).filter(project=project, status__name='Active')
        for project_user in project_users:
            # Create or retrieve the allocation user.
            allocation_user = self.__get_or_create_allocation_user(
                project_user, allocation)
            # Create or retrieve the allocation user's Service Units attribute.
            # Set its value.
            allocation_user_attribute = \
                self.__get_or_create_allocation_user_attribute(
                    allocation_user, 'Service Units', str(value))
            # A usage object should exist for the allocation user attribute.
            try:
                AllocationUserAttributeUsage.objects.get(
                    allocation_user_attribute=allocation_user_attribute)
            except AllocationUserAttributeUsage.DoesNotExist:
                raise AllocationUserAttributeUsage.DoesNotExist(
                    f'Unexpected: No AllocationUserAttributeUsage object '
                    f'exists for AllocationUserAttribute '
                    f'{allocation_user_attribute}.')

            # If the user has a cluster_uid, create or retrieve the allocation
            # user's Cluster Account Status attribute. Set its value to
            # 'Active'.
            if not project_user.user.userprofile.cluster_uid:
                continue
            self.__get_or_create_allocation_user_attribute(
                allocation_user, 'Cluster Account Status', 'Active')

    def create_vector_allocations(self, allocation_user_status_choice=None):
        """Create allocations to the Vector Compute resource for Vector
        projects, allocation users, and allocation user attributes
        denoting that each user has cluster access.

        Parameters:
            - None

        Returns:
            - None

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if a given Project has more than
            allocation to the Vector Compute resource
        """
        projects = Project.objects.prefetch_related(
            'allocation_set__status', 'allocation_set__resources',
            'projectuser_set',
        ).filter(name__startswith='vector_', status__name='Active')
        for project in projects:
            # Create or retrieve the project's allocation to the Vector Compute
            # resource, of which there should be only one.
            allocation = self.__get_or_create_allocation(project)
            # Set cluster account statuses for each of the project's users.
            project_users = project.projectuser_set.prefetch_related(
                'status', 'user__userprofile').filter(status__name='Active')
            for project_user in project_users:
                # Create or retrieve the allocation user.
                allocation_user = self.__get_or_create_allocation_user(
                    project_user, allocation)
                # If the user has a cluster_uid, create or retrieve the
                # allocation user's Cluster Account Status attribute. Set its
                # value to 'Active'.
                if not project_user.user.userprofile.cluster_uid:
                    continue
                self.__get_or_create_allocation_user_attribute(
                    allocation_user, 'Cluster Account Status', 'Active')

    def create_abc_allocations(self):
        """Create allocations to the ABC Compute resource for the abc
        project, allocation users, and allocation user attributes
        denoting that each user has cluster access.

        Parameters:
            - None

        Returns:
            - None

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if a given Project has more than
            allocation to the ABC Compute resource
        """
        name = 'abc'
        try:
            project = Project.objects.prefetch_related(
                'allocation_set__status', 'allocation_set__resources',
                'projectuser_set',
            ).get(name=name, status__name='Active')
        except Project.DoesNotExist:
            self.logger.error(f'Expected Project {name} does not exist.')
            return
        # Create or retrieve the project's allocation to the ABC Compute
        # resource, of which there should be only one.
        allocation = self.__get_or_create_allocation(project)
        # Set cluster account statuses for each of the project's users.
        project_users = project.projectuser_set.prefetch_related(
            'status', 'user__userprofile').filter(status__name='Active')
        for project_user in project_users:
            # Create or retrieve the allocation user.
            allocation_user = self.__get_or_create_allocation_user(
                project_user, allocation)
            # If the user has a cluster_uid, create or retrieve the
            # allocation user's Cluster Account Status attribute. Set its
            # value to 'Active'.
            if not project_user.user.userprofile.cluster_uid:
                continue
            self.__get_or_create_allocation_user_attribute(
                allocation_user, 'Cluster Account Status', 'Active')

    def __get_or_create_allocation(self, project):
        """Get or create an Allocation to the correct Compute Resource
        for the given Project.

        Parameters:
            - project (Project): the Project instance to get or create
            the Allocation for

        Returns:
            - The retrieved or created Allocation

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if a given Project has more than
            one allocation to the Compute resource
        """
        resource = Resource.objects.get(
            name=get_project_compute_resource_name(project))
        allocation_status_choice = AllocationStatusChoice.objects.get(
            name='Active')
        allocations = project.allocation_set.filter(resources=resource)
        if allocations.count() == 0:
            allocation = Allocation.objects.create(
                project=project, status=allocation_status_choice)
            allocation.resources.add(resource)
            allocation.save()
            self.logger.info(
                f'Allocation for Project {project.name} to Resource '
                f'{resource.name} was created.')
        elif allocations.count() == 1:
            allocation = allocations.first()
            allocation.status = allocation_status_choice
            allocation.save()
        else:
            raise MultipleObjectsReturned(
                f'Unexpected: Project {project.name} has more than one '
                f'Allocation to Resource {resource.name}.')
        return allocation

    def __get_or_create_allocation_user(self, project_user, allocation):
        """Get or create an AllocationUser for the given ProjectUser and
        Allocation. Set its status to 'Active'.

        Parameters:
            - project_user (ProjectUser): the ProjectUser instance to
            get or create the AllocationUser for
            - allocation (Allocation): the Allocation instance to create
            the AllocationUser under

        Returns:
            - The retrieved or created AllocationUser

        Raises:
            - None
        """
        allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
            name='Active')
        try:
            allocation_user = AllocationUser.objects.get(
                allocation=allocation, user=project_user.user)
        except AllocationUser.DoesNotExist:
            allocation_user = AllocationUser.objects.create(
                allocation=allocation, user=project_user.user,
                status=allocation_user_status_choice)
            self.logger.info(
                f'AllocationUser for Allocation {allocation.pk} and '
                f'User {project_user.user.username} was created.')
        else:
            allocation_user.status = allocation_user_status_choice
            allocation_user.save()
        return allocation_user

    def __get_or_create_allocation_attribute(self, allocation, type_name,
                                             value):
        """Get or create an AllocationAttribute having the type with the
        given name for the given Allocation. Set its value.

        Parameters:
            - allocation (Allocation): the Allocation instance to create
            or update the attribute for
            - type_name (str): the name of the AllocationAttributeType
            - value (str): the value to set for the attribute

        Returns:
            - The retrieved or created AllocationAttribute

        Raises:
           - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if more than one attribute is
            found
        """
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name=type_name)
        allocation_attribute, created = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)
        if created:
            self.logger.info(
                f'AllocationAttribute with type '
                f'{allocation_attribute_type.name} for Allocation '
                f'{allocation.pk} was created.')
        allocation_attribute.value = value
        allocation_attribute.save()
        return allocation_attribute

    def __get_or_create_allocation_user_attribute(self, allocation_user,
                                                  type_name, value):
        """Get or create an AllocationUserAttribute having the type with
        the given name for the given AllocationUser. Set its value.

        Parameters:
            - allocation_user (AllocationUser): the AllocationUser
            instance to create or update the attribute for
            - type_name (str): the name of the AllocationAttributeType
            - value (str): the value to set for the attribute

        Returns:
            - The retrieved or created AllocationUserAttribute

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if more than one attribute is
            found
        """
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name=type_name)
        allocation = allocation_user.allocation
        allocation_user_attribute, created = \
            AllocationUserAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation, allocation_user=allocation_user)
        if created:
            self.logger.info(
                f'AllocationUserAttribute with type '
                f'{allocation_attribute_type.name} for AllocationUser '
                f'{allocation_user.pk} was created.')
        allocation_user_attribute.value = value
        allocation_user_attribute.save()
        return allocation_user_attribute
