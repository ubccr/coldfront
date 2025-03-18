from coldfront.core.project.models import ProjectStatusChoice, Project

from coldfront.core.resource.models import ResourceType, Resource
from django.test import TestCase
from coldfront.core.allocation.forms import AllocationForm
from django.contrib.auth import get_user_model

from coldfront.core.school.models import School


class AllocationFormTest(TestCase):
    """Tests for AllocationForm resource restriction by school."""

    def setUp(self):
        self.user = get_user_model().objects.create(username="testuser")

        # Create schools
        self.school_a = School.objects.create(description='Tandon School of Engineering')
        self.school_b = School.objects.create(description='Center for Data Science')
        # Create projects under different schools
        status = ProjectStatusChoice.objects.create(name='Active')
        self.project_a = Project.objects.create(title="Project A", description="test", school=self.school_a, pi=self.user, status=status)
        self.project_b = Project.objects.create(title="Project B", description="Test", school=self.school_b, pi=self.user, status=status)

        # Create resources under different schools
        cluster = ResourceType.objects.create(name='Cluster', description='Cluster servers')
        generic = ResourceType.objects.create(name='Generic', description='Generic School')
        self.resource_a = Resource.objects.create(
                resource_type=generic,
                parent_resource=None,
                name='Tandon',
                description='Tandon-wide-resources',
                school=self.school_a,
                is_available=True,
                is_public=False,
                is_allocatable=True
            )
        self.resource_b = Resource.objects.create(
                resource_type=generic,
                parent_resource=None,
                name='CDS',
                description='CDS-wide-resources',
                school=self.school_b,
                is_available=True,
                is_public=False,
                is_allocatable=True
            )
        self.resource_uni = Resource.objects.create(
                resource_type=cluster,
                parent_resource=None,
                name='University HPC',
                description='General University HPC',
                school=None,
                is_available=True,
                is_public=True,
                is_allocatable=True
            )

    def test_allocation_form_restricts_resources_by_school(self):
        """Test that AllocationForm only includes resources from the same school as the project."""
        form = AllocationForm(self.user, self.project_a.pk)
        available_resources = form.fields['resource'].queryset

        self.assertIn(self.resource_a, available_resources)  # Resource A should be included
        self.assertNotIn(self.resource_b, available_resources)  # Resource B should be excluded
        self.assertIn(self.resource_uni, available_resources)  # University HPC should be always included

