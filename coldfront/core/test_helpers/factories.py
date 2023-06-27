from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

import factory
from factory import SubFactory
from faker import Faker
from faker.providers import BaseProvider, DynamicProvider
from factory.django import DjangoModelFactory

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.resource.models import ResourceType, Resource
# from coldfront.core.department.models import Department
from coldfront.core.project.models import (Project,
                                            ProjectUser,
                                            ProjectAttribute,
                                            ProjectAttributeType,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice,
                                            ProjectStatusChoice,
                                            AttributeType as PAttributeType
                                        )
from coldfront.core.allocation.models import (Allocation,
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
                                            AttributeType as AAttributeType
                                        )
from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.core.publication.models import PublicationSource



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
     provider_name="fieldofscience",
     elements=['Chemistry', 'Physics', 'Economics', 'Biology', 'Statistics', 'Astrophysics'],
)

fake.add_provider(ColdfrontProvider)
fake.add_provider(field_of_science_provider)


### User factories ###

class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ('username',)
    username = fake.unique.username()
    email = factory.LazyAttribute(lambda obj: '%s@example.com' % obj.username)
    is_staff = False
    is_active = True
    is_superuser = False


### Field of Science factories ###

class FieldOfScienceFactory(DjangoModelFactory):
    class Meta:
        model = FieldOfScience
        django_get_or_create = ('description',)

    description = fake.fieldofscience()


### Department factories ###

# class DepartmentFactory(DjangoModelFactory):
#     class Meta:
#         model = Department




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
        django_get_or_create = ('name',)
    name = 'Active'


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ('title',)

    pi = SubFactory(UserFactory)
    title = fake.unique.project_title()
    description = fake.sentence()
    field_of_science = SubFactory(FieldOfScienceFactory)
    status = SubFactory(ProjectStatusChoiceFactory)
    force_review = False
    requires_review = False
    # force_review = fake.boolean()
    # requires_review = fake.boolean()

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
    name='Text'

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
    name = fake.unique.resource_name()

    description = fake.sentence()
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
        django_get_or_create = ('project',)
    justification = fake.sentence()
    status = SubFactory(AllocationStatusChoiceFactory)
    project = SubFactory(ProjectFactory)
    # definition of the many-to-many "resources" field using the ResourceFactory
    # to automatically generate one or more of the required Resource objects
    # @post_generation
    # def resources(self, create, extracted, **kwargs):
    #     if not create:
    #         return
    #     if extracted:
    #         for resource in extracted:
    #             self.resources.add(resource)
    #     else:
    #         self.resources.add(ResourceFactory())


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
    justification = fake.sentence()

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
    note = fake.sentence()



def setup_models(test_case):
    """Set up models that we use in multiple tests"""

    for status in ['Active', 'New', 'Inactive', 'Paid', 'Ready for Review']:
        AllocationStatusChoiceFactory(name=status)
    for status in ['Active', 'Inactive', 'New', 'Archived']:
        ProjectStatusChoiceFactory(name=status)
    for attribute_type in ['Date', 'Int', 'Float', 'Text', 'Boolean']:
        AAttributeTypeFactory(name=attribute_type)
    for status in ['Pending', 'Approved', 'Denied']:
        AllocationChangeStatusChoiceFactory(name=status)
    for alloc_attr_type in ['Storage Quota (TB)']:
        AllocationAttributeTypeFactory(name=alloc_attr_type, is_private=False, is_changeable=True)
    # users
    test_case.admin_user = UserFactory(username='gvanrossum', is_staff=True, is_superuser=True)
    # pi is a project admin but not an AllocationUser.
    test_case.pi_user = UserFactory(username='sdpoisson',
                                            is_staff=False, is_superuser=False)
    test_case.proj_allocation_user = UserFactory(username='ljbortkiewicz',
                                            is_staff=False, is_superuser=False)
    test_case.proj_nonallocation_user = UserFactory(username='wkohn',
                                            is_staff=False, is_superuser=False)
    test_case.nonproj_allocation_user = UserFactory(username='jsaul',
                                            is_staff=False, is_superuser=False)
    test_case.project = ProjectFactory(pi=test_case.pi_user, title="poisson_lab")

    # allocations
    test_case.proj_allocation = AllocationFactory(
                    project=test_case.project,
                    is_changeable=True,
                )
    test_case.proj_allocation.resources.add(ResourceFactory(name='holylfs10/tier1', id=1))

    # make a quota_bytes allocation attribute
    allocation_quota = AllocationQuotaFactory(allocation=test_case.proj_allocation, value=109951162777600)
    AllocationAttributeUsageFactory(allocation_attribute=allocation_quota, value=10995116277760)
    # make a quota TB allocation attribute
    allocation_quota_tb = AllocationAttributeFactory(allocation=test_case.proj_allocation,
        value = 100,
        allocation_attribute_type=AllocationAttributeTypeFactory(name='Storage Quota (TB)'),
                     )
    AllocationAttributeUsageFactory(allocation_attribute=allocation_quota_tb, value=10)
    # relationships
    AllocationUserFactory(user=test_case.proj_allocation_user, allocation=test_case.proj_allocation)
    AllocationUserFactory(user=test_case.nonproj_allocation_user, allocation=test_case.proj_allocation)


    manager_role = ProjectUserRoleChoiceFactory(name='Manager')

    ProjectUserFactory(user=test_case.pi_user, project=test_case.project, role=manager_role)
    test_case.normal_projuser = ProjectUserFactory(user=test_case.proj_allocation_user,
                                                    project=test_case.project)
    ProjectUserFactory(user=test_case.proj_nonallocation_user, project=test_case.project)
