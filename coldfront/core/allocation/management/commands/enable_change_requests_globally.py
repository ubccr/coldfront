# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation


class Command(BaseCommand):
    help = "Enable change requests on all allocations"

    def handle(self, *args, **options):
        answer = input(f"Enable change requests on all {Allocation.objects.count()} allocations? [y/N]: ")
        if answer == "Y" or answer == "y":
            Allocation.objects.all().update(is_changeable=True)
