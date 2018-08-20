from django.db import models

from model_utils.models import TimeStampedModel

from core.djangoapps.project.models import Project




class Publication(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    author = models.CharField(max_length=1024)
    publication_date = models.DateField()
    unique_id = models.CharField('DOI or Bibliographic Code', max_length=1024, null=True,blank=True,)
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Archived', 'Archived'),
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='Active')
