# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.management.base import BaseCommand

from coldfront.core.project.models import (
    AttributeType,
    ProjectAttributeType,
    ProjectReviewStatusChoice,
    ProjectStatusChoice,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)


class Command(BaseCommand):
    help = "Add default project related choices"

    def handle(self, *args, **options):
        for choice in [
            "New",
            "Active",
            "Archived",
        ]:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        for choice in [
            "Completed",
            "Pending",
        ]:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        for choice in [
            "User",
            "Manager",
        ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        for choice in [
            "Active",
            "Pending - Add",
            "Pending - Remove",
            "Denied",
            "Removed",
        ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        for attribute_type in ("Date", "Float", "Int", "Text", "Yes/No"):
            AttributeType.objects.get_or_create(name=attribute_type)

        for name, attribute_type, has_usage, is_private in (
            ("Project ID", "Text", False, False),
            ("Account Number", "Int", False, True),
        ):
            ProjectAttributeType.objects.get_or_create(
                name=name,
                attribute_type=AttributeType.objects.get(name=attribute_type),
                has_usage=has_usage,
                is_private=is_private,
            )
