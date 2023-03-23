from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.resource.models import ResourceType
from coldfront.core.project.models import Project, ProjectStatusChoice
from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.core.publication.models import PublicationSource

from django.contrib.auth.models import User

from factory.django import DjangoModelFactory
from factory import SubFactory

from coldfront.core.utils.common import import_from_settings
PUBLICATION_ENABLE = import_from_settings('PUBLICATION_ENABLE', False)

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User


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

if PUBLICATION_ENABLE:
    class PublicationSourceFactory(DjangoModelFactory):
        class Meta:
            model = PublicationSource

        name = 'doi'
        url = 'https://doi.org/'


class ResourceTypeFactory(DjangoModelFactory):
    class Meta:
        model = ResourceType
