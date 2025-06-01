# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


def add_project_status_choices(apps, schema_editor):
    ProjectStatusChoice = apps.get_model("project", "ProjectStatusChoice")

    for choice in [
        "New",
        "Active",
        "Archived",
    ]:
        ProjectStatusChoice.objects.get_or_create(name=choice)


def add_project_user_role_choices(apps, schema_editor):
    ProjectUserRoleChoice = apps.get_model("project", "ProjectUserRoleChoice")

    for choice in [
        "User",
        "Manager",
    ]:
        ProjectUserRoleChoice.objects.get_or_create(name=choice)


def add_project_user_status_choices(apps, schema_editor):
    ProjectUserStatusChoice = apps.get_model("project", "ProjectUserStatusChoice")

    for choice in [
        "Active",
        "Pending Remove",
        "Denied",
        "Removed",
    ]:
        ProjectUserStatusChoice.objects.get_or_create(name=choice)


def generate_project_code(project_code: str, project_pk: int, padding: int = 0) -> str:
    """
    Generate a formatted project code by combining an uppercased user-defined project code,
    project primary key and requested padding value (default = 0).

    :param project_code: The base project code, set through the PROJECT_CODE configuration variable.
    :param project_pk: The primary key of the project.
    :param padding: The number of digits to pad the primary key with, set through the PROJECT_CODE_PADDING configuration variable.
    :return: A formatted project code string.
    """

    return f"{project_code.upper()}{str(project_pk).zfill(padding)}"
