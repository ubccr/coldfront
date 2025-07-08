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


def determine_automated_institution_choice(project, institution_map: dict):
    """
    Determine automated institution choice for a project. Taking PI email of current project
    and comparing to domain key from institution_map. Will first try to match a domain exactly
    as provided in institution_map, if a direct match cannot be found an indirect match will be
    attempted by looking for the first occurrence of an institution domain that occurs as a substring
    in the PI's email address. This does not save changes to the database. The project object in
    memory will have the institution field modified.
    :param project: Project to add automated institution choice to.
    :param institution_map: Dictionary of institution keys, values.
    """
    email: str = project.pi.email

    try:
        _, pi_email_domain = email.split("@")
    except ValueError:
        pi_email_domain = None

    direct_institution_match = institution_map.get(pi_email_domain)

    if direct_institution_match:
        project.institution = direct_institution_match
        return direct_institution_match
    else:
        for institution_email_domain, indirect_institution_match in institution_map.items():
            if institution_email_domain in pi_email_domain:
                project.institution = indirect_institution_match
                return indirect_institution_match

    return project.institution
