from factory import (
    DjangoModelFactory,
    SubFactory,
)

from django.contrib.auth.models import User
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
)
from coldfront.core.publication.models import PublicationSource


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User


class FieldOfScienceFactory(DjangoModelFactory):
    class Meta:
        model = FieldOfScience


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
