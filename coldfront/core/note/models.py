from django.db import models

from coldfront.core.allocation.models import Allocation, AllocationNoteTags
from coldfront.core.user.models import User
import datetime
import importlib
import logging
from ast import literal_eval
from enum import Enum

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import mark_safe
from django.utils.module_loading import import_string
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project, ProjectPermission
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import import_from_settings
import coldfront.core.attribute_expansion as attribute_expansion

# Create your models here.


class NoteTags(TimeStampedModel):
    name = models.CharField(max_length=64)

    class NoteTagManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)
    objects = NoteTagManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    class Meta:
        ordering = ['name', ]


class Note(TimeStampedModel):
    """ A project user message is a message sent to a user in a project. 
    
    Attributes:
        project (Project): links the project the message is from to the message
        author (User): represents the user who authored the message
        is_private (bool): indicates whether or not the message is private
        message (str): text input from the user containing the message
    """


    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE,null=True)
    project = models.ForeignKey(Project,on_delete=models.CASCADE, null=True)
    title = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)
    tags = models.ForeignKey(NoteTags, on_delete=models.CASCADE,null=True,default=None)
    test = models.TextField(default="True")
    is_private = models.BooleanField(default=False)
    message = models.TextField()
    # note_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="NoteTo",null=True)
    message = models.TextField()

    def __str__(self):
        return self.message
class Comment(TimeStampedModel):
    """ An allocation user note is a note that an user makes on an allocation.
    
    Attributes:
        allocation (Allocation): links the allocation to the note
        author (User): represents the User class of the user who authored the note
        is_private (bool): indicates whether or not the note is private
        note (str): text input from the user containing the note
    """

    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)
    note = models.TextField()

    def __str__(self):
        return self.note
    