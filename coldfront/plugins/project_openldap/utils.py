# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin utils.py"""

import logging
import textwrap
from typing import Any, Tuple

from ldap3 import BASE, MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.core.results import RESULT_NO_SUCH_ATTRIBUTE, RESULT_NO_SUCH_OBJECT, RESULT_SUCCESS
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
    * Add members to a posixgroup in OpenLDAP
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(Connection.modify, dn, {"memberUid": [(MODIFY_ADD, list_memberuids)]}, write=write)


def remove_members_from_openldap_posixgroup(dn, list_memberuids, write=True):
    """
    * Remove members from a posixgroup in OpenLDAP
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(Connection.modify, dn, {"memberUid": [(MODIFY_DELETE, list_memberuids)]}, write=write)


def add_per_project_ou_to_openldap(project_obj, dn, openldap_ou_description, write=True):
    """
    * Add a per project OU to OpenLDAP - write an OU for a project
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(
        Connection.add,
        dn,
        ["top", "organizationalUnit"],
        {"ou": project_obj.project_code, "description": openldap_ou_description},
        write=write,
    )


def add_posixgroup_to_openldap(dn, openldap_description, gid_int, write=True):
    """
    * Add a posixGroup to OpenLDAP
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(
        Connection.add,
        dn,
        "posixGroup",
        {"description": openldap_description, "gidNumber": gid_int},
        write=write,
    )


# Remove a DN - e.g. DELETE a project OU or posixgroup in OpenLDAP
def remove_dn_from_openldap(dn, write=True):
    """
    * Remove a DN from OpenLDAP
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(Connection.delete, dn, write=write)


# Update the project title in OpenLDAP
def update_posixgroup_description_in_openldap(dn, openldap_description, write=True):
    """
    * Update the description of a posixGroup in OpenLDAP
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(Connection.modify, dn, {"description": [(MODIFY_REPLACE, [openldap_description])]}, write=write)


# MOVE the project to an archive OU - defined as env var
def move_dn_in_openldap(current_dn, relative_dn, destination_ou, write=True):
    """
    * Move a DN to another OU in OpenLDAP
    * if not `write`, adds log message and does nothing
    * Should not raise any exceptions
    * returns `True` if skipped or successful, `False` if failed
    """
    _ldap_write_wrapper(Connection.modify_dn, current_dn, relative_dn, new_superior=destination_ou, write=write)


def ldapsearch_check_project_dn(dn):
    """
    * Check a distinguished name exists and represents a project (posixGroup)
    * raises `LDAPException` if the `ldap3.Connection` cannot be established or if the `ldap3.Result` code is nonzero
    """
    _, success = _ldap_read_wrapper(Connection.search, dn, "(objectclass=posixGroup)", BASE)
    return success


# check bind user can see the Project OU or Archive OU - is also used in system setup check script
def ldapsearch_check_ou(OU):
    """
    * Test that ldapsearch can see an OU
    * raises `LDAPException` if the `ldap3.Connection` cannot be established or if the `ldap3.Result` code is nonzero
    """
    _, success = _ldap_read_wrapper(Connection.search, OU, "(objectclass=organizationalUnit)", BASE)
    return success


def ldapsearch_get_posixgroup_memberuids(dn):
    """
    * Get memberUids from a project's posixGroup
    * raises `LDAPException` if the `ldap3.Connection` cannot be established or if the `ldap3.Result` code is nonzero
    * raises `KeyError` if the `entries` attribute of the `ldap3.Connection` is empty
    """
    entries, _ = _ldap_read_wrapper(Connection.search, dn, "(objectclass=posixGroup)", BASE, attributes=["memberUid"])
    if len(entries) == 0:
        raise KeyError(dn)
    return entries


def ldapsearch_get_description(dn):
    """
    * Get description from an openldap entry
    * raises `LDAPException` if the `ldap3.Connection` cannot be established or if the `ldap3.Result` code is nonzero
    * raises `KeyError` if the `entries` attribute of the `ldap3.Connection` is empty
    """
    entries, _ = _ldap_read_wrapper(Connection.search, dn, "(objectclass=posixGroup)", BASE, attributes=["description"])
    if len(entries) == 0:
        raise KeyError(dn)
    return entries


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


def _connection(read_only=False):
    return Connection(
        server, PROJECT_OPENLDAP_BIND_USER, PROJECT_OPENLDAP_BIND_PASSWORD, auto_bind=True, read_only=read_only
    )


def _ldap_write_wrapper(func, *args, write=True, **kwargs) -> bool:
    """
    * if not `write`, adds log message and does nothing
    * inserts an `ldap3.Connection` as the 1st argument to `func`
        * `func` should probably be a method of `ldap3.Connection` whose 1st argument is `self`
    * exceptions are caught and logged
    * returns `True` if skipped or successful, `False` if failed
    """
    logger_extra_data = dict(funcname=func.__name__, args=args, kwargs=kwargs)
    if not write:
        logger.info(f"dry run, skipping... - {logger_extra_data}")
        return True
    try:
        conn = _connection()
    except LDAPException:
        logger.exception(f"Failed to open LDAP connection - {logger_extra_data}", exc_info=True)
        return False
    try:
        func(conn, *args, **kwargs)
    except Exception:
        logger.exception(f"An unexpected exception occurred! - {logger_extra_data}", exc_info=True)
        return False
    finally:
        conn.unbind()
    if conn.result["result"] != RESULT_SUCCESS:
        logger.error(f"LDAP operation failed! - {logger_extra_data}")
        return False
    return True


def _ldap_read_wrapper(func, *args, **kwargs) -> Tuple[list, Any]:
    """
    * inserts an `ldap3.Connection` as the 1st argument to `func`
        * `func` should probably be a method of `ldap3.Connection` whose 1st argument is `self`
    * raises `LDAPException` if the ldap3.Connection cannot be established or if the ldap3.Result code is unexpected
    * returns (ldap3.Connection.entries, whatever `func` returns)
    """
    conn = _connection(read_only=True)
    try:
        output = func(conn, *args, **kwargs)
        entries = conn.entries.copy()
    finally:
        conn.unbind()
    if conn.result["result"] not in [RESULT_SUCCESS, RESULT_NO_SUCH_OBJECT, RESULT_NO_SUCH_ATTRIBUTE]:
        raise LDAPException(conn.result)
    return entries, output
