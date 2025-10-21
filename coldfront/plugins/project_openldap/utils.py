# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin utils.py"""

import logging
import textwrap
from contextlib import contextmanager
from typing import Any, Generator, Tuple

from ldap3 import MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.log import ERROR, set_library_log_detail_level

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

# activate ldap3's builtin logging
set_library_log_detail_level(ERROR)

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


def add_members_to_openldap_posixgroup(dn, list_memberuids, write=True):
    """
    Add members to a posixgroup in OpenLDAP
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper("modify", dn, {"memberUid": [(MODIFY_ADD, list_memberuids)]}, write=write)


def remove_members_from_openldap_posixgroup(dn, list_memberuids, write=True):
    """
    Remove members from a posixgroup in OpenLDAP
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper("modify", dn, {"memberUid": [(MODIFY_DELETE, list_memberuids)]}, write=write)


def add_per_project_ou_to_openldap(project_obj, dn, openldap_ou_description, write=True):
    """
    Add a per project OU to OpenLDAP - write an OU for a project
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper(
        "add",
        dn,
        ["top", "organizationalUnit"],
        {"ou": project_obj.project_code, "description": openldap_ou_description},
        write=write,
    )


def add_posixgroup_to_openldap(dn, openldap_description, gid_int, write=True):
    """
    Add a posixGroup to OpenLDAP
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper(
        "add", dn, "posixGroup", {"description": openldap_description, "gidNumber": gid_int}, write=write
    )


# Remove a DN - e.g. DELETE a project OU or posixgroup in OpenLDAP
def remove_dn_from_openldap(dn, write=True):
    """
    Remove a DN from OpenLDAP
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper("delete", dn, write=write)


# Update the project title in OpenLDAP
def update_posixgroup_description_in_openldap(dn, openldap_description, write=True):
    """
    Update the description of a posixGroup in OpenLDAP
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper("modify", dn, {"description": [(MODIFY_REPLACE, [openldap_description])]}, write=write)


# MOVE the project to an archive OU - defined as env var
def move_dn_in_openldap(current_dn, relative_dn, destination_ou, write=True):
    """
    Move a DN to another OU in OpenLDAP
    Should not raise any exceptions
    returns True if not skipped and successful, False otherwise
    """
    return _ldap_write_wrapper("modify_dn", current_dn, relative_dn, new_superior=destination_ou, write=write)


def ldapsearch_check_project_dn(dn):
    """
    Check a distinguished name exists and represents a project (posixGroup)
    Should not raise any exceptions
    raises LDAPException
    """
    _, output = _ldap_read_wrapper("search", dn, "(objectclass=posixGroup)")
    return output


# check bind user can see the Project OU or Archive OU - is also used in system setup check script
def ldapsearch_check_ou(OU):
    """
    Test that ldapsearch can see an OU
    raises LDAPException
    """
    _, output = _ldap_read_wrapper("search", OU, "(objectclass=organizationalUnit)")
    return output


def ldapsearch_get_posixgroup_memberuids(dn):
    """
    Get memberUids from a project's posixGroup
    raises LDAPException
    raises KeyError if search has no results
    """
    conn, _ = _ldap_read_wrapper("search", dn, "(objectclass=posixGroup)", attributes=["memberUid"])
    if len(conn.entries) == 0:
        raise KeyError(dn)
    return conn.entries


def ldapsearch_get_description(dn):
    """
    Get description from an openldap entry
    raises LDAPException
    raises KeyError if search has no results
    """
    conn, _ = _ldap_read_wrapper("search", dn, "(objectclass=posixGroup)", attributes=["description"])
    if len(conn.entries) == 0:
        raise KeyError(dn)
    return conn.entries


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
    return f"ou={project_obj.project_code},{PROJECT_OPENLDAP_OU}"


def construct_ou_archived_dn_str(project_obj):
    """Create a distinguished name (dn) for a per project ou - archived"""
    return f"ou={project_obj.project_code},{PROJECT_OPENLDAP_ARCHIVE_OU}"


def construct_dn_str(project_obj):
    """Create a distinguished name (dn) for a project posixgroup in a per project ou, in the projects ou"""
    return f"cn={project_obj.project_code},ou={project_obj.project_code},{PROJECT_OPENLDAP_OU}"


def construct_dn_archived_str(project_obj):
    """Create a distinguished name (dn) for a project posixgroup in a per project ou, in the archive ou"""
    return f"cn={project_obj.project_code},ou={project_obj.project_code},{PROJECT_OPENLDAP_ARCHIVE_OU}"


def construct_per_project_ou_relative_dn_str(project_obj):
    """Create a relative distinguished name (rdn) for a project ou - required when moving this object to a new superior e.g. archive ou"""
    return f"ou={project_obj.project_code}"


def construct_project_ou_description(project_obj):
    """Create a description for a per project OU"""
    return f"OU for project {project_obj.project_code}"


def construct_project_posixgroup_description(project_obj):
    """Create a description for a project's posixGroup"""
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


@contextmanager
def _connection(*args, **kwargs) -> Generator[Connection, LDAPException]:
    try:
        conn = Connection(*args, **kwargs)
    except LDAPException as e:
        return e
    try:
        yield conn
    finally:
        conn.unbind()


def _ldap_write_wrapper(funcname, *args, **kwargs) -> bool:
    logger_extra_data = dict(funcname=funcname, args=args, kwargs=kwargs)
    if not kwargs.pop("write", True):
        logger.info("write is falsey, skipping...", stack_info=True, extra=logger_extra_data)
        return False
    with _connection(server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD, auto_bind=True) as conn:
        if isinstance(conn, LDAPException):
            logger.error("Failed to open LDAP connection", exc_info=conn, extra=logger_extra_data)
            return False
        func = getattr(conn, funcname)
        try:
            func(*args, **kwargs)
        except Exception:
            logger.exception("An unexpected exception occurred!", exc_info=True, extra=logger_extra_data)
            return False
    if conn.result["result"] != 0:
        logger.error("LDAP operation failed!", stack_info=True, extra=logger_extra_data)
        return False
    return True


def _ldap_read_wrapper(funcname, *args, **kwargs) -> Tuple[Connection, Any]:
    with _connection(
        server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD, auto_bind=True, read_only=True
    ) as conn:
        if isinstance(conn, LDAPException):
            raise conn
        func = getattr(conn, funcname)
        output = func(*args, **kwargs)
    if conn.result["result"] != 0:
        raise LDAPException(conn)
    return conn, output
