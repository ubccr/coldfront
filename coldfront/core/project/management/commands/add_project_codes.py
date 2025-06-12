# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.management.base import BaseCommand

from coldfront.core.project.models import Project
from coldfront.core.project.utils import generate_project_code
from coldfront.core.utils.common import import_from_settings

PROJECT_CODE = import_from_settings("PROJECT_CODE", False)
PROJECT_CODE_PADDING = import_from_settings("PROJECT_CODE_PADDING", False)


class Command(BaseCommand):
    help = "Update existing projects with project codes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Outputting project primary keys and titled, followed by their updated project code",
        )

    def update_project_code(self, projects):
        user_input = input(
            "Assign all existing projects with project codes? You can use the --dry-run flag to preview changes first. [y/N] "
        )

        try:
            if user_input == "y" or user_input == "Y":
                for project in projects:
                    project.project_code = generate_project_code(PROJECT_CODE, project.pk, PROJECT_CODE_PADDING)
                    project.save(update_fields=["project_code"])
                self.stdout.write(f"Updated {projects.count()} projects with project codes")
            else:
                self.stdout.write("No changes made")
        except AttributeError:
            self.stdout.write(
                "Error, no changes made. Please set PROJECT_CODE as a string value inside configuration file."
            )

    def project_code_dry_run(self, projects):
        try:
            for project in projects:
                new_code = generate_project_code(PROJECT_CODE, project.pk, PROJECT_CODE_PADDING)
                self.stdout.write(
                    f"Project {project.pk}, called {project.title}: new project_code would be '{new_code}'"
                )
        except AttributeError:
            self.stdout.write(
                "Error, no changes made. Please set PROJECT_CODE as a string value inside configuration file."
            )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        projects_without_codes = Project.objects.filter(project_code="")

        if dry_run:
            self.project_code_dry_run(projects_without_codes)
        else:
            self.update_project_code(projects_without_codes)
