from django.db import models
from django.conf import settings

from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

from coldfront.core.project.models import Project


class DepartmentRank(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Department(TimeStampedModel):
    """
    All entities in nanites_organization where rank != lab. If biller
    is True, Coldfront will generate invoices for the Department.
    """
    name = models.CharField(max_length=255,)
    rank = models.ForeignKey(DepartmentRank, on_delete=models.CASCADE)
    projects = models.ManyToManyField(Project, through='DepartmentProject')
    biller = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    history = HistoricalRecords()


    class Meta:
        ordering = ['name',]


class DepartmentProject(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    history = HistoricalRecords()


class DepartmentMemberRole(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class DepartmentMemberStatus(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']



class DepartmentMember(TimeStampedModel):
    """connect User records with Department records, specify relationship qualities.
    """
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    role = models.ForeignKey(DepartmentMemberRole, on_delete=models.CASCADE)
    status = models.ForeignKey(DepartmentMemberStatus, on_delete=models.CASCADE)
    enable_notifications = models.BooleanField(default=True)
    history = HistoricalRecords()
