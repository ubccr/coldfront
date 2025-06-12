# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.management.base import BaseCommand

from coldfront.core.project.models import Project
from coldfront.core.project.utils import add_automated_institution_choice
from coldfront.core.utils.common import import_from_settings

PROJECT_INSTITUTION_EMAIL_MAP = import_from_settings("PROJECT_INSTITUTION_EMAIL_MAP", False)


class Command(BaseCommand):
    help = "Update existing projects with institutions based on PIs email address"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Outputs each project, followed by the assigned institution, without making changes.",
        )

    def update_project_institution(self, projects):
        if not PROJECT_INSTITUTION_EMAIL_MAP:
            self.stdout.write(
                "Error, no changes made. Please set PROJECT_INSTITUTION_EMAIL_MAP as a dictionary value inside configuration file."
            )
            return

        user_input = input(
            "Assign all existing projects with institutions? You can use the --dry-run flag to preview changes first. [y/N] "
        )

        try:
            if user_input == "y" or user_input == "Y":
                for project in projects:
                    project.institution = add_automated_institution_choice(project, PROJECT_INSTITUTION_EMAIL_MAP)
                    project.save(update_fields=["institution"])
                self.stdout.write(f"Updated {projects.count()} projects with institutions.")
            else:
                self.stdout.write("No changes made")
        except Exception as e:
            self.stdout.write(f"Error: {e}")

    def institution_dry_run(self, projects):
        if not PROJECT_INSTITUTION_EMAIL_MAP:
            self.stdout.write(
                "Error, no changes made. Please set PROJECT_INSTITUTION_EMAIL_MAP as a dictionary value inside configuration file."
            )
            return

        try:
            for project in projects:
                new_institution = add_automated_institution_choice(project, PROJECT_INSTITUTION_EMAIL_MAP)
                self.stdout.write(
                    f"Project {project.pk}, called {project.title}. Institution would be '{new_institution}'"
                )
        except Exception as e:
            self.stdout.write(f"Error: {e}")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        projects_without_institution = Project.objects.filter(institution="None")

        if dry_run:
            self.institution_dry_run(projects_without_institution)
        else:
            self.update_project_institution(projects_without_institution)
