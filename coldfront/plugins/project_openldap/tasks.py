# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin tasks.py"""

import logging

from coldfront.core.project.models import ProjectUser
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.project_openldap.utils import (
    add_members_to_openldap_project_posixgroup,
    add_per_project_ou_to_openldap,
    add_project_posixgroup_to_openldap,
    allocate_project_openldap_gid,
    archive_project_in_openldap,
    construct_dn_str,
    construct_ou_dn_str,
    construct_per_project_ou_relative_dn_str,
    construct_project_ou_description,
    construct_project_posixgroup_description,
    remove_dn_from_openldap,
    remove_members_from_openldap_project_posixgroup,
    update_project_posixgroup_in_openldap,
)

# Setup logging
logger = logging.getLogger(__name__)

# Note:
# OpenLDAP server connection definitions are handled in utils.py

# Environment variables for OpenLDAP functionality.
PROJECT_OPENLDAP_OU = import_from_settings("PROJECT_OPENLDAP_OU")
PROJECT_OPENLDAP_GID_START = import_from_settings("PROJECT_OPENLDAP_GID_START")
PROJECT_OPENLDAP_REMOVE_PROJECT = import_from_settings(
    "PROJECT_OPENLDAP_REMOVE_PROJECT"
)  # defaults to True in plugin settings
PROJECT_OPENLDAP_ARCHIVE_OU = import_from_settings("PROJECT_OPENLDAP_ARCHIVE_OU")


def add_project(project_obj):
    """Method to add project to OpenLDAP - uses signals for project creation"""

    # if project_code not enabled or None or empty, print appropriate message and bail out to avoid adding it to OpenLDAP
    if not hasattr(project_obj, "project_code"):
        logger.info("Enable project_code to use the project_openldap plugin to add projects into OpenLDAP")
        logger.info(
            "Additional message - this issue was encountered with project pk %s",
            {project_obj.pk},
        )
        return None
    if project_obj.project_code in [None, ""]:
        logger.WARNING("None or empty project_code value encountered, please run the project code management command")
        logger.WARNING(
            "Additional message - this issue was encountered with project pk %s",
            {project_obj.pk},
        )
        return None

    # 1) first make the OU for the project
    openldap_ou_description = construct_project_ou_description(project_obj)
    ou_dn = construct_ou_dn_str(project_obj)
    logger.info("Adding OpenLDAP project OU entry - DN: %s", ou_dn)

    add_per_project_ou_to_openldap(project_obj, ou_dn, openldap_ou_description)

    # 2) then make the posixgroup
    posixgroup_dn = construct_dn_str(project_obj)
    gid_int = allocate_project_openldap_gid(project_obj.pk, PROJECT_OPENLDAP_GID_START)
    openldap_posixgroup_description = construct_project_posixgroup_description(project_obj)

    logger.info("Adding OpenLDAP project posixgroup entry - DN: %s", posixgroup_dn)
    logger.info("Adding OpenLDAP project posixgroup entry - GID: %s", gid_int)
    logger.info(
        "Adding OpenLDAP project posixgroup entry - GID: %s",
        openldap_posixgroup_description,
    )

    add_project_posixgroup_to_openldap(posixgroup_dn, openldap_posixgroup_description, gid_int)


# Coldfront archive project action
def remove_project(project_obj):
    """Method to remove project from OpenLDAP OR place in archive - uses signals for Coldfront project archive action"""

    ou_dn = construct_ou_dn_str(project_obj)

    # if remove project (default: true) and no archive_ou defined, then remove from OpenLDAP...
    if PROJECT_OPENLDAP_REMOVE_PROJECT and not PROJECT_OPENLDAP_ARCHIVE_OU:
        # remove project's group, then project's ou
        posixgroup_dn = construct_dn_str(project_obj)
        logger.info(f"Project POSIXGROUP {posixgroup_dn} is going to be REMOVED from OpenLDAP...")
        remove_dn_from_openldap(posixgroup_dn)

        logger.info(f"Project OU {ou_dn} is going to be REMOVED from OpenLDAP...")
        remove_dn_from_openldap(ou_dn)
    # ...otherwise if archive_ou is defined, archive in OpenLDAP
    else:
        relative_dn = construct_per_project_ou_relative_dn_str(project_obj)
        logger.info(f"Project OU {ou_dn} is going to be ARCHIVED in OpenLDAP at {PROJECT_OPENLDAP_ARCHIVE_OU}...")
        archive_project_in_openldap(ou_dn, relative_dn, PROJECT_OPENLDAP_ARCHIVE_OU)


def update_project(project_obj):
    """Method to update project [title] in OpenLDAP - uses signals for project update"""
    dn = construct_dn_str(project_obj)
    logger.info(" ATTEMPTING PROJECT UPDATE IN TASKS.PY ")
    openldap_description = construct_project_posixgroup_description(project_obj)

    logger.info("Modifying OpenLDAP entry: %s", dn)
    logger.info("Modifying OpenLDAP with description: %s", openldap_description)
    update_project_posixgroup_in_openldap(dn, openldap_description)


def add_user_project(project_user_pk):
    """Method to add a user to OpenLDAP project - uses signals"""

    final_user = ProjectUser.objects.get(pk=project_user_pk)
    final_user_username = str(final_user.user.username)

    dn = construct_dn_str(final_user.project)

    logger.info("Adding to OpenLDAP entry: %s", dn)
    logger.info("memberUid: %s", final_user_username)

    list_memberuids = []
    list_memberuids.append(final_user_username)
    add_members_to_openldap_project_posixgroup(dn, list_memberuids)


def remove_user_project(project_user_pk):
    """Method to remove a user from OpenLDAP project - uses signals"""

    final_user = ProjectUser.objects.get(pk=project_user_pk)
    final_user_username = str(final_user.user.username)

    dn = construct_dn_str(final_user.project)

    logger.info("Removing OpenLDAP entry: %s", dn)
    logger.info("memberUid: %s", final_user_username)

    list_memberuids = []
    list_memberuids.append(final_user_username)
    remove_members_from_openldap_project_posixgroup(dn, list_memberuids)
