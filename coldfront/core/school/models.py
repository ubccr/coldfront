from django.db import models
from model_utils.models import TimeStampedModel

class School(TimeStampedModel):
    """ A school is a school affiliate under which a project falls. The list is prepopulated in ColdFront using the National Science Foundation FOS list, but can be changed by a center admin if needed. Examples include Chemistry and Physics.

    Attributes:
        description (str): field of science description
    """
    class Meta:
        ordering = ['description']

    class FieldOfScienceManager(models.Manager):
        def get_by_natural_key(self, description):
            return self.get(description=description)

    DEFAULT_PK = 1
    description = models.CharField(max_length=255, unique=True)
    objects = FieldOfScienceManager()

    def __str__(self):
        return self.description

    def natural_key(self):
        return [self.description]