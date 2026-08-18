# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import ChangeLogMessageSerializer, ValidatedModelSerializer
from coldfront.ras.models import ProjectInvite
from coldfront.users.api.serializers import UserSerializer

from .projects import ProjectSerializer

__all__ = ("ProjectInviteSerializer",)


class ProjectInviteSerializer(ChangeLogMessageSerializer, ValidatedModelSerializer):
    project = ProjectSerializer(nested=True)
    invited_by = UserSerializer(nested=True, required=False, allow_null=True, default=None)

    class Meta:
        model = ProjectInvite
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "email",
            "project",
            "invited_by",
            "accepted_at",
            "created",
            "last_updated",
        ]
        # The secret invite code (code_hash) is intentionally never exposed.
        brief_fields = ("id", "url", "display", "email", "project")
