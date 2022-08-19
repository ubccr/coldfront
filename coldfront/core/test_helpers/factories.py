# from factory import (
#     DjangoModelFactory,
#     SubFactory,
#     )
from django.contrib.auth import get_user_model
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.resource.models import ResourceType
from coldfront.core.project.models import Project, ProjectStatusChoice
from coldfront.core.allocation.models import Allocation
from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.core.publication.models import PublicationSource

from django.contrib.auth.models import User

from factory.django import DjangoModelFactory
from factory import SubFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()


class AllocationFactory(DjangoModelFactory):
    class Meta:
        model = Allocation


class FieldOfScienceFactory(DjangoModelFactory):
    class Meta:
        model = FieldOfScience


class GrantFundingAgencyFactory(DjangoModelFactory):
    class Meta:
        model = GrantFundingAgency


class GrantStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = GrantStatusChoice


class ProjectStatusChoiceFactory(DjangoModelFactory):
    class Meta:
        model = ProjectStatusChoice


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    title = 'Test project!'
    pi = SubFactory(UserFactory)
    description = 'This is a project description.'
    field_of_science = SubFactory(FieldOfScienceFactory)
    status = SubFactory(ProjectStatusChoiceFactory)
    force_review = False
    requires_review = False


class PublicationSourceFactory(DjangoModelFactory):
    class Meta:
        model = PublicationSource

    name = 'doi'
    url = 'https://doi.org/'


class ResourceTypeFactory(DjangoModelFactory):
    class Meta:
        model = ResourceType
