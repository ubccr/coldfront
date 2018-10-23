from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project


class PublicationSource(TimeStampedModel):
    name = models.CharField(max_length=255)
    url = models.URLField()

    def __str__(self):
        return self.name


class Publication(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    author = models.CharField(max_length=1024)
    year = models.PositiveIntegerField()
    unique_id = models.CharField(max_length=255, null=True, blank=True)
    source = models.ForeignKey(PublicationSource, on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Archived', 'Archived'),
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='Active')
    history = HistoricalRecords()


    class Meta:
        unique_together = ('project', 'unique_id')

    def __str__(self):
        return self.title
