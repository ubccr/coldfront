import factory
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from factory import SubFactory
from factory.fuzzy import FuzzyChoice
from factory.django import DjangoModelFactory
from faker import Faker
from faker.providers import BaseProvider, DynamicProvider

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.resource.models import ResourceType, Resource
from coldfront.core.project.models import (
    Project,
    ProjectUser,
    ProjectAttribute,
    ProjectAttributeType,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectStatusChoice,
    AttributeType as PAttributeType,
)
from coldfront.core.allocation.models import (
    Allocation,
    AllocationUser,
    AllocationUserNote,
    AllocationAttribute,
    AllocationStatusChoice,
    AllocationAttributeType,
    AllocationChangeRequest,
    AllocationChangeStatusChoice,
    AllocationAttributeUsage,
    AllocationUserStatusChoice,
    AllocationAttributeChangeRequest,
    AttributeType as AAttributeType,
)
from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.core.publication.models import PublicationSource


### Default values and Faker provider setup ###

project_status_choice_names = ['New', 'Active', 'Archived']
project_user_role_choice_names = ['User', 'Access Manager', 'Storage Manager', 'General Manager', 'PI']
field_of_science_names = ['Physics', 'Chemistry', 'Economics', 'Biology', 'Sociology']
attr_types = ['Date', 'Int', 'Float', 'Text', 'Boolean']

fake = Faker()

class ColdfrontProvider(BaseProvider):
    def project_title(self):
        return f'{fake.last_name()}_lab'.lower()

    def resource_name(self):
        return fake.word().lower()+ '/' + fake.word().lower()

    def username(self):
        first_name = fake.first_name()
        last_name = fake.last_name()
        return f'{first_name}{last_name}'.lower()

field_of_science_provider = DynamicProvider(
    provider_name="fieldofscience", elements=field_of_science_names,
)
attr_type_provider = DynamicProvider(provider_name="attr_types", elements=attr_types)

for provider in [ColdfrontProvider, field_of_science_provider, attr_type_provider]:
    factory.Faker.add_provider(provider)



### User factories ###

class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ('username',)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.LazyAttribute(lambda o: f'{o.first_name}{o.last_name}')
    email = factory.LazyAttribute(lambda obj: '%s@example.com' % obj.username)
    is_staff = False
    is_active = True
    is_superuser = False



### Field of Science factories ###

class FieldOfScienceFactory(DjangoModelFactory):
    class Meta:
        model = FieldOfScience
        django_get_or_create = ('description',)

    description = factory.Faker('fieldofscience')



### Grant factories ###

class GrantFundingAgencyFactory(DjangoModelFactory):
    class Meta:
        model = GrantFundingAgency


class GrantStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = GrantStatusChoice



### Project factories ###

class ProjectStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = ProjectStatusChoice
        # ensure that names are unique
        django_get_or_create = ('name',)
    # randomly generate names from list of default values
    # name = FuzzyChoice(project_status_choice_names)
    name = 'Active'


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ('title',)

    pi = SubFactory(UserFactory)
    title = factory.Faker('project_title')
    description = factory.Faker('sentence')
    field_of_science = SubFactory(FieldOfScienceFactory)
    status = SubFactory(ProjectStatusChoiceFactory)
    force_review = False
    requires_review = False


class ProjectUserRoleChoiceFactory(DjangoModelFactory):
    class Meta:
        model = ProjectUserRoleChoice
        django_get_or_create = ('name',)
    name = 'User'


class ProjectUserStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = ProjectUserStatusChoice
        django_get_or_create = ('name',)
    name = 'Active'


class ProjectUserFactory(DjangoModelFactory):
    class Meta:
        model = ProjectUser
        django_get_or_create = ('project', 'user')

    project = SubFactory(ProjectFactory)
    user = SubFactory(UserFactory)
    role = SubFactory(ProjectUserRoleChoiceFactory)
    status = SubFactory(ProjectUserStatusChoiceFactory)



### Project Attribute factories ###

class PAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = PAttributeType
        # django_get_or_create = ('name',)
    name = factory.Faker('attr_type')


class ProjectAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = ProjectAttributeType
    name = 'Test attribute type'
    attribute_type = SubFactory(PAttributeTypeFactory)


class ProjectAttributeFactory(DjangoModelFactory):
    class Meta:
        model = ProjectAttribute
    proj_attr_type = SubFactory(ProjectAttributeTypeFactory)
    value = 'Test attribute value'
    project = SubFactory(ProjectFactory)



    ### Publication factories ###

class PublicationSourceFactory(DjangoModelFactory):
    class Meta:
        model = PublicationSource

    name = 'doi'
    url = 'https://doi.org/'


### Resource factories ###

class ResourceTypeFactory(DjangoModelFactory):
    class Meta:
        model = ResourceType
        django_get_or_create = ('name',)
    name = 'Storage'

class ResourceFactory(DjangoModelFactory):
    class Meta:
        model = Resource
        django_get_or_create = ('name',)
    name = factory.Faker('resource_name')

    description = factory.Faker('sentence')
    resource_type = SubFactory(ResourceTypeFactory)



### Allocation factories ###

class AllocationStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = AllocationStatusChoice
        django_get_or_create = ('name',)
    name = 'Active'


class AllocationFactory(DjangoModelFactory):
    class Meta:
        model = Allocation
        django_get_or_create = ('project', 'justification')
    justification = factory.Faker('sentence')
    status = SubFactory(AllocationStatusChoiceFactory)
    project = SubFactory(ProjectFactory)
    is_changeable = True


### Allocation Attribute factories ###

class AAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = AAttributeType
        django_get_or_create = ('name',)
    name='Int'


class AllocationAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = AllocationAttributeType
        django_get_or_create = ('name',)
    name = 'Test attribute type'
    attribute_type = SubFactory(AAttributeTypeFactory)
    is_changeable=True


class AllocationAttributeFactory(DjangoModelFactory):
    class Meta:
        model = AllocationAttribute
    allocation_attribute_type = SubFactory(AllocationAttributeTypeFactory)
    value = 2048
    allocation = SubFactory(AllocationFactory)


class AllocationAttributeUsageFactory(DjangoModelFactory):
    class Meta:
        model = AllocationAttributeUsage
        django_get_or_create = ('allocation_attribute',)
    allocation_attribute = SubFactory(AllocationAttributeFactory)
    value = 1024

# inherited from AllocationAttributeFactory
class AllocationQuotaFactory(AllocationAttributeFactory):
    value=1073741824
    allocation_attribute_type=SubFactory(AllocationAttributeTypeFactory,
                    name='Quota_In_Bytes')
                    # name='Storage_Quota_TB')


### Allocation Change Request factories ###

class AllocationChangeStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = AllocationChangeStatusChoice
        django_get_or_create = ('name',)
    name = 'Pending'


class AllocationChangeRequestFactory(DjangoModelFactory):
    class Meta:
        model = AllocationChangeRequest

    allocation = SubFactory(AllocationFactory)
    status = SubFactory(AllocationChangeStatusChoiceFactory)
    justification = factory.Faker('sentence')


class AllocationAttributeChangeRequestFactory(DjangoModelFactory):
    class Meta:
        model = AllocationAttributeChangeRequest

    allocation_change_request = SubFactory(AllocationChangeRequestFactory)
    allocation_attribute = SubFactory(AllocationAttributeFactory)
    new_value = 1000



### Allocation User factories ###

class AllocationUserStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = AllocationUserStatusChoice
        django_get_or_create = ('name',)
    name = 'Active'


class AllocationUserFactory(DjangoModelFactory):
    class Meta:
        model = AllocationUser
        django_get_or_create = ('allocation','user')
    allocation = SubFactory(AllocationFactory)
    user = SubFactory(UserFactory)
    status = SubFactory(AllocationUserStatusChoiceFactory)
    unit = 'GB'
    usage = 100
    usage_bytes = 100000000000


class AllocationUserNoteFactory(DjangoModelFactory):
    class Meta:
        model = AllocationUserNote
        django_get_or_create = ('allocation')
    allocation = SubFactory(AllocationFactory)
    author = SubFactory(AllocationUserFactory)
    note = factory.Faker('sentence')



def setup_models(test_case):
    """Set up models that we use in multiple tests"""

    for status in ['Active', 'New', 'Inactive', 'Paid', 'Ready for Review']:
        AllocationStatusChoiceFactory(name=status)
    for status in ['Active', 'New', 'Archived']:
        ProjectStatusChoiceFactory(name=status)
    for attribute_type in ['Date', 'Int', 'Float', 'Text', 'Yes/No']:
        AAttributeTypeFactory(name=attribute_type)
    for status_choice in ['Active','Removed']:
        AllocationUserStatusChoiceFactory(name=status_choice)
    for status in ['Pending', 'Approved', 'Denied']:
        AllocationChangeStatusChoiceFactory(name=status)
    for resource_type in ['Storage', 'Cluster', 'Cluster Partition', 'Compute Node']:
        ResourceTypeFactory(name=resource_type)
    for resource, r_id, rtype in [
        ('holylfs10/tier1', 1, 'Storage'), 
        ('holylfs09/tier1', 2, 'Storage'),
        ('Test Cluster', 3, 'Cluster'),
        # ('Test Partition', 4, 'Cluster Partition'),
        # ('Test Node', 5, 'Compute Node')
    ]:
        ResourceFactory(name=resource, id=r_id, resource_type__name=rtype)

    quota_tb_type = AllocationAttributeTypeFactory(name='Storage Quota (TB)')
    for name, attribute_type, has_usage, is_private in (
        ('Offer Letter Code', 'Text', False, True),
        ('Expense Code', 'Text', False, True),
        ('Heavy IO',  'Yes/No', False, False),
        ('Mounted',  'Yes/No', False, False),
        ('High Security', 'Yes/No', False, False),
        ('DUA', 'Yes/No', False, False),
        ('External Sharing', 'Yes/No', False, False),
        ('slurm_specs', 'Text', False, False),
        ('Core Usage (Hours)', 'Int', True, False),
        ('EffectvUsage', 'Int', True, False),
        ('RequiresPayment', 'Yes/No', False, False),
    ):
        AllocationAttributeTypeFactory(
            name=name,
            attribute_type=AAttributeType.objects.get(name=attribute_type),
            has_usage=has_usage,
            is_private=is_private
        )
    # users
    test_case.admin_user = UserFactory(
        username='gvanrossum', is_staff=True, is_superuser=True
    )
    # pi is a project admin but not an AllocationUser.
    test_case.pi_user = UserFactory(username='sdpoisson')
    test_case.proj_allocationuser = UserFactory(username='ljbortkiewicz')
    test_case.proj_generalmanager = UserFactory(username='tedison')
    test_case.proj_datamanager = UserFactory(username='ajayer')
    test_case.proj_accessmanager = UserFactory(username='mdavis')
    test_case.proj_nonallocationuser = UserFactory(username='wkohn')
    test_case.nonproj_allocationuser = UserFactory(username='jsaul')
    test_case.project = ProjectFactory(pi=test_case.pi_user, title="poisson_lab")
    # cluster allocation users
    test_case.cluster_allocationuser = UserFactory(username='jdoe')
    test_case.nonproj_cluster_allocationuser = UserFactory(username='jdoe2')

    # resources
    test_case.resource_allowed_user = UserFactory(username='iberlin')
    test_case.cluster_resource = Resource.objects.get(name='Test Cluster')
    test_case.cluster_resource.allowed_users.add(test_case.resource_allowed_user)
    test_case.storage_resource = Resource.objects.get(name='holylfs10/tier1')
    test_case.storage_resource.allowed_users.add(test_case.resource_allowed_user)

    # allocations
    for alloc in ['storage test', 'compute test']:
        AllocationFactory(project=test_case.project, justification=alloc)
    test_case.storage_allocation = Allocation.objects.get(justification='storage test')
    test_case.storage_allocation.resources.add(test_case.storage_resource)

    test_case.cluster_allocation = Allocation.objects.get(justification='compute test')
    test_case.cluster_allocation.resources.add(test_case.cluster_resource)

    # make a quota_bytes allocation attribute
    allocation_quota = AllocationQuotaFactory(
        allocation=test_case.storage_allocation, value=109951162777600
    )
    AllocationAttributeUsageFactory(
        allocation_attribute=allocation_quota, value=10995116277760
    )
    # make a quota TB allocation attribute
    allocation_quota_tb = AllocationAttributeFactory(
        allocation=test_case.storage_allocation,
        value=100,
        allocation_attribute_type=quota_tb_type,
    )
    AllocationAttributeUsageFactory(allocation_attribute=allocation_quota_tb, value=10)
    # relationships
    for user in [test_case.proj_allocationuser, test_case.nonproj_allocationuser]:
        AllocationUserFactory(user=user, allocation=test_case.storage_allocation)
        AllocationUserFactory(user=user, allocation=test_case.cluster_allocation)

    for user, role in {
        test_case.pi_user:'PI',
        test_case.proj_generalmanager: 'General Manager',
        test_case.proj_datamanager: 'Storage Manager',
        test_case.proj_accessmanager: 'Access Manager',
        test_case.proj_nonallocationuser: 'User',
    }.items():
        ProjectUserFactory(
            user=user, project=test_case.project, role=ProjectUserRoleChoiceFactory(name=role)
        )

    test_case.npu = ProjectUserFactory(user=test_case.proj_allocationuser, project=test_case.project)
    test_case.normal_projuser = test_case.npu.user
