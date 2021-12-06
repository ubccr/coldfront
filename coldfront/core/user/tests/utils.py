from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from decimal import Decimal
from django.core.management import call_command
from django.test import TestCase
import os
import sys


def grant_user_cluster_access_under_test_project(user):
    """For the given User, Create a Project named 'test_project', a
    ProjectUser, an associated Allocation and AllocationUser, and an
    AllocationUserAttribute of type 'Cluster Account Status' and value
    'Active'. Return this last object."""
    project_name = 'test_project'
    project = Project.objects.create(
        name=project_name,
        status=ProjectStatusChoice.objects.get(name='Active'),
        title=project_name,
        description=f'Description of {project_name}.')
    ProjectUser.objects.create(
        project=project,
        user=user,
        role=ProjectUserRoleChoice.objects.get(name='User'),
        status=ProjectUserStatusChoice.objects.get(name='Active'))
    num_service_units = Decimal('0.00')
    create_project_allocation(project, num_service_units)
    objects = create_user_project_allocation(
        user, project, num_service_units)
    allocation = objects.allocation
    allocation_user = objects.allocation_user
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Cluster Account Status')
    return AllocationUserAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation,
        allocation_user=allocation_user,
        value='Active')


class TestUserBase(TestCase):
    """A base class for testing User-related functionality."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        sys.stdout = open(os.devnull, 'w')
        call_command('create_staff_group')
        sys.stdout = sys.__stdout__
