# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.db import models
from model_utils.models import TimeStampedModel


class FieldOfScience(TimeStampedModel):
    """A field of science is a division under which a project falls. The list is prepopulated in ColdFront using the National Science Foundation FOS list, but can be changed by a center admin if needed. Examples include Chemistry and Physics.

    Attributes:
        parent_id (FieldOfScience): represents parent field of science if it exists
        is_selectable (bool): indicates whether or not a field of science is selectable for a project
        description (str): field of science description
        fos_nsf_id (int): represents the field of science's ID under the National Science Foundation
        fos_nsf_abbrev (str): represents the field of science's abbreviation under the National Science Foundation
        directorate_fos_id (int): represents the National Science Foundation's ID for the department the field of science falls under
    """

    class Meta:
        ordering = ["description"]

    class FieldOfScienceManager(models.Manager):
        def get_by_natural_key(self, description):
            return self.get(description=description)

    DEFAULT_PK = 149
    parent_id = models.ForeignKey("self", on_delete=models.CASCADE, null=True)
    is_selectable = models.BooleanField(default=True)
    description = models.CharField(max_length=255, unique=True)
    fos_nsf_id = models.IntegerField(null=True, blank=True)
    fos_nsf_abbrev = models.CharField(max_length=10, null=True, blank=True)
    directorate_fos_id = models.IntegerField(null=True, blank=True)
    objects = FieldOfScienceManager()

    def __str__(self):
        return self.description

    def natural_key(self):
        return [self.description]
