# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import models

from coldfront.models import ColdFrontModel


class DummyModel(models.Model):
    name = models.CharField(max_length=20)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]


class DummyColdFrontModel(ColdFrontModel):
    pass
