# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin utils.py"""

import logging
import textwrap

from ldap3 import MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE, Connection, Server, Tls

from coldfront.core.utils.common import import_from_settings

PROJECT_OPENLDAP_BIND_USER = import_from_settings("PROJECT_OPENLDAP_BIND_USER")
PROJECT_OPENLDAP_BIND_PASSWORD = import_from_settings("PROJECT_OPENLDAP_BIND_PASSWORD")
PROJECT_OPENLDAP_SERVER_URI = import_from_settings("PROJECT_OPENLDAP_SERVER_URI")

PROJECT_OPENLDAP_OU = import_from_settings("PROJECT_OPENLDAP_OU")

PROJECT_OPENLDAP_CONNECT_TIMEOUT = import_from_settings("PROJECT_OPENLDAP_CONNECT_TIMEOUT")
PROJECT_OPENLDAP_USE_SSL = import_from_settings("PROJECT_OPENLDAP_USE_SSL")
PROJECT_OPENLDAP_USE_TLS = import_from_settings("PROJECT_OPENLDAP_USE_TLS")
PROJECT_OPENLDAP_PRIV_KEY_FILE = import_from_settings("PROJECT_OPENLDAP_PRIV_KEY_FILE")
PROJECT_OPENLDAP_CERT_FILE = import_from_settings("PROJECT_OPENLDAP_CERT_FILE")
PROJECT_OPENLDAP_CACERT_FILE = import_from_settings("PROJECT_OPENLDAP_CACERT_FILE")
PROJECT_OPENLDAP_ARCHIVE_OU = import_from_settings("PROJECT_OPENLDAP_ARCHIVE_OU")

PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH = import_from_settings("PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH")

# provide a sensible default locally to stop the openldap description being too long
MAX_OPENLDAP_DESCRIPTION_LENGTH = 250

# Note: SASL not provided currently

tls = None
if PROJECT_OPENLDAP_USE_TLS:
    tls = Tls(
        local_private_key_file=PROJECT_OPENLDAP_PRIV_KEY_FILE,
        local_certificate_file=PROJECT_OPENLDAP_CERT_FILE,
        ca_certs_file=PROJECT_OPENLDAP_CACERT_FILE,
    )


server = Server(
    PROJECT_OPENLDAP_SERVER_URI,
    use_ssl=PROJECT_OPENLDAP_USE_SSL,
    connect_timeout=PROJECT_OPENLDAP_CONNECT_TIMEOUT,
    tls=tls,
)
logger = logging.getLogger(__name__)


def openldap_connection(server_opt, bind_user, bind_password):
    """Open connection to OpenLDAP"""
    try:
        connection = Connection(server_opt, bind_user, bind_password, auto_bind=True)
        return connection
    except Exception as e:
        logger.error("Could not connect to OpenLDAP server: %s", e)
        return None


def add_members_to_openldap_project_posixgroup(dn, list_memberuids, write=True):
    """Add members to a posixgroup in OpenLDAP"""
    member_uid = tuple(list_memberuids)
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    try:
        for user in member_uid:
            add_username = user
            conn.modify(dn, {"memberUid": [(MODIFY_ADD, [add_username])]})
    except Exception as exc_log:
        logger.info(exc_log)
    finally:
        conn.unbind()


def remove_members_from_openldap_project_posixgroup(dn, list_memberuids, write=True):
    """Remove members from a posixgroup in OpenLDAP"""
    member_uids_tuple = tuple(list_memberuids)
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    try:
        for user in member_uids_tuple:
            remove_username = user
            conn.modify(dn, {"memberUid": [(MODIFY_DELETE, [remove_username])]})
    except Exception as exc_log:
        logger.info(exc_log)
    finally:
        conn.unbind()


def add_per_project_ou_to_openldap(project_obj, dn, openldap_ou_description, write=True):
    """Add a per project OU to OpenLDAP - write an OU for a project"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    # project code is used for ou, other components were supplied from construction methods to this function
    try:
        project_code_str = project_obj.project_code
        ou = f"{project_code_str}"
        conn.add(
            dn,
            ["top", "organizationalUnit"],
            {"ou": ou, "description": openldap_ou_description},
        )
    except Exception as exc_log:
        logger.error("Project OU: DN to write...")
        logger.error(f"dn - {dn}")
        logger.error("Attributes to write...")
        logger.error(f"OU description - {openldap_ou_description}")
        logger.error(exc_log)
    finally:
        conn.unbind()


def add_project_posixgroup_to_openldap(dn, openldap_description, gid_int, write=True):
    """Add a project to OpenLDAP - write a posixGroup"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    try:
        conn.add(
            dn,
            "posixGroup",
            {"description": openldap_description, "gidNumber": gid_int},
        )
    except Exception as exc_log:
        logger.error("Project posixgroup: DN to write...")
        logger.error(f"dn - {dn}")
        logger.error("Attributes to write...")
        logger.error(f"posixGroup description - {openldap_description} gidNumber - {gid_int}")
        logger.error(exc_log)
    finally:
        conn.unbind()


# Remove a DN - e.g. DELETE a project OU or posixgroup in OpenLDAP
def remove_dn_from_openldap(dn, write=True):
    """Remove a project from OpenLDAP - delete a posixGroup"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    try:
        conn.delete(dn)
        conn.unbind()
        conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)
    except Exception as exc_log:
        logger.info(exc_log)
    finally:
        conn.unbind()


# Update the project title in OpenLDAP
def update_project_posixgroup_in_openldap(dn, openldap_description, write=True):
    """Update the description of a posixGroup in OpenLDAP"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    try:
        conn.modify(dn, {"description": [(MODIFY_REPLACE, [openldap_description])]})
        conn.unbind()
    except Exception as exc_log:
        logger.info(exc_log)
    finally:
        conn.unbind()


# MOVE the project to an archive OU - defined as env var
def archive_project_in_openldap(current_dn, relative_dn, archive_ou, write=True):
    """Move a project to the archive OU in OpenLDAP"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    if not write:
        return None

    try:
        conn.modify_dn(current_dn, relative_dn, new_superior=archive_ou)
        conn.unbind()
    except Exception as exc_log:
        logger.info(exc_log)
    finally:
        conn.unbind()


def ldapsearch_check_project_dn(dn):
    """Check a distinguished name exists and represents a project (posixGroup)"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    try:
        ldapsearch_check_project_dn_result = conn.search(dn, "(objectclass=posixGroup)")
        return ldapsearch_check_project_dn_result
    except Exception as exc_log:
        logger.info(exc_log)
        return None
    finally:
        conn.unbind()


# check bind user can see the Project OU or Archive OU - is also used in system setup check script
def ldapsearch_check_project_ou(OU):
    """Test that ldapsearch can see an OU"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    try:
        ldapsearch_check_project_ou_result = conn.search(OU, "(objectclass=organizationalUnit)")
        return ldapsearch_check_project_ou_result
    except Exception as exc_log:
        logger.info(exc_log)
        return None
    finally:
        conn.unbind()


def ldapsearch_get_project_memberuids(dn):
    """Get memberUids from a project's posixGroup"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    try:
        conn.search(dn, "(objectclass=posixGroup)", attributes=["memberUid"])
        ldapsearch_project_memberuids_entries = conn.entries
        return ldapsearch_project_memberuids_entries
    except Exception as exc_log:
        logger.info(exc_log)
        return None
    finally:
        conn.unbind()


def ldapsearch_get_project_description(dn):
    """Get description from a project's posixGroup"""
    conn = openldap_connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD)

    if not conn:
        return

    try:
        conn.search(dn, "(objectclass=posixGroup)", attributes=["description"])
        ldapsearch_project_description_entries = conn.entries
        # list with single entry, get description
        ldapsearch_project_description = ldapsearch_project_description_entries[0].description
        return ldapsearch_project_description
    except Exception as exc_log:
        logger.info(exc_log)
        return None
    finally:
        conn.unbind()


"""
    Allocate GID function.
"""


# Provides linear/contiguous GID allocations, using the project object's pk
def allocate_project_openldap_gid(project_pk, PROJECT_OPENLDAP_GID_START):
    """Create a GID for use as gidNumber in the project's posixGroup"""
    # add the GID start
    project_pkid_int = int(project_pk)
    gid_int = project_pkid_int + PROJECT_OPENLDAP_GID_START

    # example result 8000+PK if starting at 8000
    allocated_project_openldap_gid = int(gid_int)

    return allocated_project_openldap_gid


"""
    Construction functions.
"""


def construct_ou_dn_str(project_obj):
    """Create a distinguished name (dn) for a per project ou"""
    try:
        project_code_str = project_obj.project_code
        dn = f"ou={project_code_str},{PROJECT_OPENLDAP_OU}"
        return dn
    except Exception as exc_log:
        logger.info(exc_log)
        return None


def construct_ou_archived_dn_str(project_obj):
    """Create a distinguished name (dn) for a per project ou - archived"""
    try:
        project_code_str = project_obj.project_code
        dn = f"ou={project_code_str},{PROJECT_OPENLDAP_ARCHIVE_OU}"
        return dn
    except Exception as exc_log:
        logger.info(exc_log)
        return None


def construct_dn_str(project_obj):
    """Create a distinguished name (dn) for a project posixgroup in a per project ou, in the projects ou"""
    try:
        project_code_str = project_obj.project_code
        dn = f"cn={project_code_str},ou={project_code_str},{PROJECT_OPENLDAP_OU}"
        return dn
    except Exception as exc_log:
        logger.info(exc_log)
        return None


def construct_dn_archived_str(project_obj):
    """Create a distinguished name (dn) for a project posixgroup in a per project ou, in the archive ou"""
    try:
        project_code_str = project_obj.project_code
        dn = f"cn={project_code_str},ou={project_code_str},{PROJECT_OPENLDAP_ARCHIVE_OU}"
        return dn
    except Exception as exc_log:
        logger.info(exc_log)
        return None


def construct_per_project_ou_relative_dn_str(project_obj):
    """Create a relative distinguished name (rdn) for a project ou - required when moving this object to a new superior e.g. archive ou"""
    try:
        project_code_str = project_obj.project_code
        relative_dn = f"ou={project_code_str}"
        return relative_dn
    except Exception as exc_log:
        logger.info(exc_log)
        return None


def construct_project_ou_description(project_obj):
    """Create a description for a per project OU"""
    try:
        project_code_str = project_obj.project_code
        description = f"OU for project {project_code_str}"
        return description
    except Exception as exc_log:
        logger.info(exc_log)
        return None


def construct_project_posixgroup_description(project_obj):
    """Create a description for a project's posixGroup"""
    try:
        pi = project_obj.pi

        # if title is too long shorten
        if len(project_obj.title) > PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH:
            truncated_title = textwrap.shorten(
                project_obj.title,
                PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH,
                placeholder="...",
            )
            title = truncated_title
        else:
            title = project_obj.title

        description = ""

        # if institution feature activated use in OpenLDAP description
        if hasattr(project_obj, "institution"):
            institution = project_obj.institution
            # set to NotDefined if empty
            if project_obj.institution in [None, ""]:
                institution = "NotDefined"
            # setup description with institution var
            description = f"INSTITUTE: {institution} | PI: {pi} | TITLE: {title}"
        else:
            # setup description without institution var
            description = f"PI: {pi} | TITLE: {title}"

        # also deal with the combined  description field, if it gets too long
        if len(description) > MAX_OPENLDAP_DESCRIPTION_LENGTH:
            truncated_description = textwrap.shorten(description, MAX_OPENLDAP_DESCRIPTION_LENGTH, placeholder="...")
            description = truncated_description

        return description
    except Exception as exc_log:
        logger.info(exc_log)
        return None
