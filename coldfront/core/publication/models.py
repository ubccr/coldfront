# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project


class PublicationSource(TimeStampedModel):
    """A publication source is a source that a publication is cited/ derived from. Examples include doi and adsabs.

    Attributes:
        name (str): source name
        url (URL): links to the url of the source
    """

    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.name


class Publication(TimeStampedModel):
    """A publication source is a source that a publication is cited/ derived from. Examples include doi and adsabs.

    Attributes:
        project (Project): links the publication to its project
        title (str): publication title
        author (str): publication author's name
        year (int): year of publication
        journal (str): journal name
        unique_id (str): publication ID
        source (PublicationSource): represents the source of the publication
        status (str): publication status
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    author = models.CharField(max_length=1024)
    year = models.PositiveIntegerField()
    journal = models.CharField(max_length=1024)
    unique_id = models.CharField(max_length=255, null=True, blank=True)
    source = models.ForeignKey(PublicationSource, on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Archived", "Archived"),
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="Active")
    history = HistoricalRecords()

    class Meta:
        unique_together = ("project", "unique_id")

    def __str__(self):
        return self.title

    def display_uid(self):
        return self.unique_id
