# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.forms import ModelForm

from coldfront.core.research_output.models import ResearchOutput


class ResearchOutputForm(ModelForm):
    class Meta:
        model = ResearchOutput
        exclude = [
            "project",
        ]
