from django.db import models
from model_utils.models import TimeStampedModel


class School(TimeStampedModel):
    """A school is a school affiliate under which a project falls. The list is prepopulated in ColdFront using the
    school affiliations list. Examples include Arts & Science and College of Dentistry.

    Attributes:
        description (str): school description
    """

    class Meta:
        ordering = ["description"]

    class SchoolManager(models.Manager):
        def get_by_natural_key(self, description):
            return self.get(description=description)

    DEFAULT_PK = 1
    description = models.CharField(max_length=255, unique=True)
    objects = SchoolManager()

    def __str__(self):
        return self.description

    def natural_key(self):
        return [self.description]
