# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import factory
from django.contrib.auth.models import User
from factory import SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice
from faker import Faker
from faker.providers import BaseProvider, DynamicProvider

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeChangeRequest,
    AllocationAttributeType,
    AllocationAttributeUsage,
    AllocationChangeRequest,
    AllocationChangeStatusChoice,
    AllocationStatusChoice,
    AllocationUser,
    AllocationUserNote,
    AllocationUserStatusChoice,
)
from coldfront.core.allocation.models import (
    AttributeType as AAttributeType,
)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.core.project.models import (
    AttributeType as PAttributeType,
)
from coldfront.core.project.models import (
    Project,
    ProjectAttribute,
    ProjectAttributeType,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.publication.models import PublicationSource
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.user.models import UserProfile

### Default values and Faker provider setup ###

project_status_choice_names = ["New", "Active", "Archived"]
project_user_role_choice_names = ["User", "Manager"]
field_of_science_names = ["Physics", "Chemistry", "Economics", "Biology", "Sociology"]
attr_types = ["Date", "Int", "Float", "Text", "Boolean"]

fake = Faker()


class ColdfrontProvider(BaseProvider):
    def project_title(self):
        return f"{fake.last_name()}_lab".lower()

    def resource_name(self):
        return fake.word().lower() + "/" + fake.word().lower()

    def username(self):
        first_name = fake.first_name()
        last_name = fake.last_name()
        return f"{first_name}{last_name}".lower()


field_of_science_provider = DynamicProvider(provider_name="fieldofscience", elements=field_of_science_names)
attr_type_provider = DynamicProvider(provider_name="attr_types", elements=attr_types)

for provider in [ColdfrontProvider, field_of_science_provider, attr_type_provider]:
    factory.Faker.add_provider(provider)


### User factories ###


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    # username = factory.Faker('username')
    username = factory.LazyAttribute(lambda o: f"{o.first_name}{o.last_name}")
    email = factory.LazyAttribute(lambda o: "%s@example.com" % o.username)


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    is_pi = False
    user = SubFactory(UserFactory)


### Field of Science factories ###


class FieldOfScienceFactory(DjangoModelFactory):
    class Meta:
        model = FieldOfScience
        django_get_or_create = ("description",)

    # description = FuzzyChoice(field_of_science_names)
    description = factory.Faker("fieldofscience")


### Grant factories ###


class GrantFundingAgencyFactory(DjangoModelFactory):
    class Meta:
        model = GrantFundingAgency


class GrantStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = GrantStatusChoice


### Project factories ###


class ProjectStatusChoiceFactory(DjangoModelFactory):
    """Factory for ProjectStatusChoice model"""

    class Meta:
        model = ProjectStatusChoice
        # ensure that names are unique
        django_get_or_create = ("name",)

    # randomly generate names from list of default values
    name = FuzzyChoice(project_status_choice_names)


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ("title",)

    pi = SubFactory(UserFactory)
    title = factory.Faker("project_title")
    description = factory.Faker("sentence")
    field_of_science = SubFactory(FieldOfScienceFactory)
    status = SubFactory(ProjectStatusChoiceFactory)
    force_review = False
    requires_review = False


class ProjectUserRoleChoiceFactory(DjangoModelFactory):
    class Meta:
        model = ProjectUserRoleChoice
        django_get_or_create = ("name",)

    name = "User"


class ProjectUserStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = ProjectUserStatusChoice
        django_get_or_create = ("name",)

    name = "Active"


class ProjectUserFactory(DjangoModelFactory):
    class Meta:
        model = ProjectUser
        django_get_or_create = ("project", "user")

    project = SubFactory(ProjectFactory)
    user = SubFactory(UserFactory)
    role = SubFactory(ProjectUserRoleChoiceFactory)
    status = SubFactory(ProjectUserStatusChoiceFactory)


### Project Attribute factories ###


class PAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = PAttributeType
        # django_get_or_create = ('name',)

    name = factory.Faker("attr_type")


class ProjectAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = ProjectAttributeType

    name = "Test attribute type"
    attribute_type = SubFactory(PAttributeTypeFactory)


class ProjectAttributeFactory(DjangoModelFactory):
    class Meta:
        model = ProjectAttribute

    proj_attr_type = SubFactory(ProjectAttributeTypeFactory)
    value = "Test attribute value"
    project = SubFactory(ProjectFactory)


### Publication factories ###


class PublicationSourceFactory(DjangoModelFactory):
    class Meta:
        model = PublicationSource

    name = "doi"
    url = "https://doi.org/"


### Resource factories ###


class ResourceTypeFactory(DjangoModelFactory):
    class Meta:
        model = ResourceType
        django_get_or_create = ("name",)

    name = "Storage"


class ResourceFactory(DjangoModelFactory):
    class Meta:
        model = Resource
        django_get_or_create = ("name",)

    name = factory.Faker("resource_name")

    description = factory.Faker("sentence")
    resource_type = SubFactory(ResourceTypeFactory)


### Allocation factories ###


class AllocationStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = AllocationStatusChoice
        django_get_or_create = ("name",)

    name = "Active"


class AllocationFactory(DjangoModelFactory):
    class Meta:
        model = Allocation
        django_get_or_create = ("project",)

    justification = factory.Faker("sentence")
    status = SubFactory(AllocationStatusChoiceFactory)
    project = SubFactory(ProjectFactory)
    is_changeable = True


### Allocation Attribute factories ###


class AAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = AAttributeType
        django_get_or_create = ("name",)

    name = "Int"


class AllocationAttributeTypeFactory(DjangoModelFactory):
    class Meta:
        model = AllocationAttributeType
        django_get_or_create = ("name",)

    name = "Test attribute type"
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
        django_get_or_create = ("allocation_attribute",)

    allocation_attribute = SubFactory(AllocationAttributeFactory)
    value = 1024


### Allocation Change Request factories ###


class AllocationChangeStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = AllocationChangeStatusChoice
        django_get_or_create = ("name",)

    name = "Pending"


class AllocationChangeRequestFactory(DjangoModelFactory):
    class Meta:
        model = AllocationChangeRequest

    allocation = SubFactory(AllocationFactory)
    status = SubFactory(AllocationChangeStatusChoiceFactory)
    justification = factory.Faker("sentence")


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
        django_get_or_create = ("name",)

    name = "Active"


class AllocationUserFactory(DjangoModelFactory):
    class Meta:
        model = AllocationUser
        django_get_or_create = ("allocation", "user")

    allocation = SubFactory(AllocationFactory)
    user = SubFactory(UserFactory)
    status = SubFactory(AllocationUserStatusChoiceFactory)


class AllocationUserNoteFactory(DjangoModelFactory):
    class Meta:
        model = AllocationUserNote
        django_get_or_create = "allocation"

    allocation = SubFactory(AllocationFactory)
    author = SubFactory(AllocationUserFactory)
    note = factory.Faker("sentence")
