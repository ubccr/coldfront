from django.db import models
from model_utils.models import TimeStampedModel


class FieldOfScience(TimeStampedModel):
    DEFAULT_PK = 149
    parent_id = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    is_selectable = models.BooleanField(default=True)
    description = models.CharField(max_length=255)
    fos_nsf_id = models.IntegerField(null=True, blank=True)
    fos_nsf_abbrev = models.CharField(max_length=10, null=True, blank=True)
    directorate_fos_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ['description']
