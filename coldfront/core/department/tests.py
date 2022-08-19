from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.core.test_helpers.factories import (
    FieldOfScienceFactory,
    ProjectStatusChoiceFactory,
    UserFactory,
)

from coldfront.core.department.models import Department

# test that pages load correctly
