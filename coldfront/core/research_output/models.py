# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project


class ResearchOutput(TimeStampedModel):
    """A research output represents anything related a project that would not fall under the publication section. Examples include magazine or newspaper articles, media coverage, databases, software, or other products created.

    Attributes:
        project (Project): links project to research output
        title (str): title of research output
        description (str): description of output
        created_by (User): represents the User model of the user creating the output
    """

    # core fields
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=128, blank=True)
    description = models.TextField(
        validators=[MinLengthValidator(3)],
    )

    # auxiliary fields
    created_by = models.ForeignKey(
        User,
        editable=False,
        on_delete=models.SET_NULL,  # don't want to remove the entry when author user is deleted
        null=True,
    )

    # automatic fields
    created = models.DateTimeField(auto_now_add=True, editable=False)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        """Saves the research output."""
        if not self.pk:
            # ensure that created_by is set initially - preventing most
            # accidental omission
            #
            # this field won't be autopopulated by Django and must instead be
            # populated by the code that adds the ResearchOutput to the
            # database
            if not self.created_by:
                raise ValueError("Model INSERT must set a created_by User")

        # since title is optional, we want to simplify and standardize "no title" entries
        # we do this at the model layer to ensure as consistent behavior as possible
        self.title = self.title.strip()

        super().save(*args, **kwargs)
