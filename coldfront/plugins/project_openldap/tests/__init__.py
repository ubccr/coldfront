# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from ldap3 import BASE, MOCK_SYNC, OFFLINE_SLAPD_2_4, Connection, Server

from coldfront.core.project.models import Project
from coldfront.core.test_helpers.factories import (
    ProjectFactory,
    ProjectUserFactory,
    UserFactory,
)
from coldfront.core.user.models import User
from coldfront.plugins.project_openldap import tasks


class ProjectOpenLdapTestCase(TestCase):
    nonarchived_projects_ou: str
    archived_projects_ou: str
    mock_server: Server
    mock_connection: Connection

    @classmethod
    def setUpClass(cls):
        call_command("add_default_project_choices")
        super(ProjectOpenLdapTestCase, cls).setUpClass()

    def _setUp(self, gid_start=0):
        root_ou = "dc=example,dc=edu"
        bind_username = "bind_username"
        bind_dn = f"cn={bind_username},{root_ou}"
        bind_password = "bind_password"
        self.nonarchived_projects_ou = f"ou=projects,{root_ou}"
        self.archived_projects_ou = f"ou=archive,{root_ou}"
        self.mock_server = Server("mock_ldap", get_info=OFFLINE_SLAPD_2_4)
        self.mock_connection = Connection(
            self.mock_server, user=bind_dn, password=bind_password, client_strategy=MOCK_SYNC
        )
        self.mock_connection.strategy.add_entry(root_ou, {"objectClass": ["top", "domain"], "dc": ["example"]})
        self.mock_connection.strategy.add_entry(
            self.nonarchived_projects_ou, {"objectClass": ["top", "organizationalUnit"], "ou": ["projects"]}
        )
        self.mock_connection.strategy.add_entry(
            self.archived_projects_ou, {"objectClass": ["top", "organizationalUnit"], "ou": ["archive"]}
        )
        self.mock_connection.strategy.add_entry(
            bind_dn,
            {"objectClass": ["top", "person"], "cn": ["foo"], "sn": ["bar"], "userPassword": [bind_password]},
        )

        def _connection(read_only=False):
            """
            in real life, _connection returns a brand new connection every time it is called
            in testing, the same connection must always be re-used for previous changes to persist
            the read_only property is overwritten for each "new" connection
            this is very fragile - there should only ever be one "live" connection at a time
            as soon as another connection is created, any previous connections should be discarded
            """
            self.mock_connection.read_only = read_only
            self.mock_connection.bind()
            return self.mock_connection

        self.conn_patch = patch("coldfront.plugins.project_openldap.utils._connection", side_effect=_connection)
        self.conn_patch.start()
        self.addCleanup(self.conn_patch.stop)
        self.tasks_constants_patch = patch.multiple(
            tasks,
            PROJECT_OPENLDAP_OU=self.nonarchived_projects_ou,
            PROJECT_OPENLDAP_ARCHIVE_OU=self.archived_projects_ou,
            PROJECT_OPENLDAP_GID_START=gid_start,
            PROJECT_OPENLDAP_REMOVE_PROJECT=True,
        )
        self.tasks_constants_patch.start()
        self.addCleanup(self.tasks_constants_patch.stop)
        self.utils_constants_patch = patch.multiple(
            "coldfront.plugins.project_openldap.utils",
            PROJECT_OPENLDAP_OU=self.nonarchived_projects_ou,
            PROJECT_OPENLDAP_ARCHIVE_OU=self.archived_projects_ou,
            PROJECT_OPENLDAP_BIND_USER=bind_dn,
            PROJECT_OPENLDAP_BIND_PASSWORD=bind_password,
            PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH=100,
        )
        self.utils_constants_patch.start()
        self.addCleanup(self.utils_constants_patch.stop)
        self.sync_constants_patch = patch.multiple(
            "coldfront.plugins.project_openldap.management.commands.project_openldap_sync",
            PROJECT_OPENLDAP_OU=self.nonarchived_projects_ou,
            PROJECT_OPENLDAP_ARCHIVE_OU=self.archived_projects_ou,
            PROJECT_OPENLDAP_GID_START=gid_start,
            PROJECT_OPENLDAP_REMOVE_PROJECT=True,
            PROJECT_OPENLDAP_EXCLUDE_USERS=[],
        )
        self.sync_constants_patch.start()
        self.addCleanup(self.sync_constants_patch.stop)

    def _create_project_with_members(self, member_usernames: list[str]) -> Project:
        pi: User = UserFactory()
        project: Project = ProjectFactory(pi=pi, status__name="Active")
        ProjectUserFactory(project=project, user=pi)
        for username in member_usernames:
            ProjectUserFactory(project=project, user__username=username)
        project.save()
        return project

    def _does_entry_exist(self, dn, objectClass) -> bool:
        self.mock_connection.bind()
        try:
            return self.mock_connection.search(dn, f"(objectclass={objectClass})", search_scope=BASE)
        finally:
            self.mock_connection.unbind()

    def _get_entry_attribute(self, dn: str, attribute: str):
        self.mock_connection.bind()
        try:
            self.mock_connection.search(dn, "(objectclass=posixGroup)", search_scope=BASE, attributes=[attribute])
            self.assertEqual(len(self.mock_connection.entries), 1)
            return self.mock_connection.entries[0][attribute]
        finally:
            self.mock_connection.unbind()

    def _get_entry_memberUid(self, dn: str) -> set[str]:
        return set(self._get_entry_attribute(dn, "memberUid"))

    def _get_entry_description(self, dn: str) -> str:
        return str(self._get_entry_attribute(dn, "description"))

    def _get_entry_gidNumber(self, dn: str) -> int:
        return int(str(self._get_entry_attribute(dn, "gidNumber")))

    def _get_project_nonArchived_ou_dn(self, project: Project) -> str:
        return f"ou={project.project_code},{self.nonarchived_projects_ou}"

    def _get_project_nonArchived_posixGroup_dn(self, project: Project) -> str:
        return f"cn={project.project_code},ou={project.project_code},{self.nonarchived_projects_ou}"

    def _get_project_archived_ou_dn(self, project: Project) -> str:
        return f"ou={project.project_code},{self.archived_projects_ou}"

    def _get_project_archived_posixGroup_dn(self, project: Project) -> str:
        return f"cn={project.project_code},ou={project.project_code},{self.archived_projects_ou}"

    def _is_user_in_nonArchived_ldap_group(self, user: User, project: Project):
        dn = self._get_project_nonArchived_posixGroup_dn(project)
        self.assertTrue(self._does_entry_exist(dn, "posixGroup"))
        return user.username in self._get_entry_memberUid(dn)
