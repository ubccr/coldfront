# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
import string
from unittest.mock import patch

from coldfront.core.project.models import Project, ProjectStatusChoice
from coldfront.core.test_helpers.factories import (
    ProjectUserRoleChoiceFactory,
    UserFactory,
)
from coldfront.plugins.project_openldap.management.commands import project_openldap_sync

from . import ProjectOpenLdapTestCase


class SyncTest(ProjectOpenLdapTestCase):
    def setUp(self):
        ProjectOpenLdapTestCase._setUp(self)
        super().setUp()

    def _sync(self, project: Project, **kwargs):
        command = project_openldap_sync.Command()
        command.sync_check_project(project.project_code, sync=True, **kwargs)

    def test_create(self):
        project = self._create_project_with_members([])
        nonArchived_ou_dn = self._get_project_nonArchived_ou_dn(project)
        self.assertFalse(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))
        self._sync(project)
        self.assertTrue(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))

    def test_delete(self):
        with (
            patch.object(project_openldap_sync, "PROJECT_OPENLDAP_REMOVE_PROJECT", True),
            patch.object(project_openldap_sync, "PROJECT_OPENLDAP_ARCHIVE_OU", ""),
        ):
            project = self._create_project_with_members([])
            nonArchived_ou_dn = self._get_project_nonArchived_ou_dn(project)
            self.assertFalse(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))
            self._sync(project)
            self.assertTrue(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))
            project.status = ProjectStatusChoice.objects.get(name="Archived")
            project.save()
            self._sync(project)
            self.assertFalse(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))

    def test_archive(self):
        project = self._create_project_with_members([])
        archived_ou_dn = self._get_project_archived_ou_dn(project)
        nonArchived_ou_dn = self._get_project_nonArchived_ou_dn(project)
        self.assertFalse(self._does_entry_exist(archived_ou_dn, "organizationalUnit"))
        self.assertFalse(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))
        self._sync(project)
        self.assertFalse(self._does_entry_exist(archived_ou_dn, "organizationalUnit"))
        self.assertTrue(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))
        project.status = ProjectStatusChoice.objects.get(name="Archived")
        project.save()
        self._sync(project, write_to_archive=False)
        self.assertFalse(self._does_entry_exist(archived_ou_dn, "organizationalUnit"))
        self.assertTrue(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))
        self._sync(project, write_to_archive=True)
        self.assertTrue(self._does_entry_exist(archived_ou_dn, "organizationalUnit"))
        self.assertFalse(self._does_entry_exist(nonArchived_ou_dn, "organizationalUnit"))

    def test_add_member_uid(self):
        project = self._create_project_with_members([])
        user = UserFactory()
        self._sync(project)
        self.assertNotIn(user.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project)))
        project.add_user(user, ProjectUserRoleChoiceFactory())
        project.save()
        self._sync(project)
        self.assertIn(user.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project)))

    def test_remove_member_uid(self):
        user = UserFactory()
        project = self._create_project_with_members([user.username])
        self._sync(project)  # for some reason users are not added when a project is first created
        self._sync(project)
        self.assertTrue(self._is_user_in_nonArchived_ldap_group(user, project))
        self.assertIn(user.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project)))
        project.remove_user(user)
        project.save()
        self._sync(project)
        self.assertFalse(self._is_user_in_nonArchived_ldap_group(user, project))

    def test_update_posixGroup_description(self):
        title_after = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        project = self._create_project_with_members([])
        self._sync(project)
        description_before = self._get_entry_description(self._get_project_nonArchived_posixGroup_dn(project))
        title_before = project.title
        self.assertIn(title_before, description_before)
        self.assertNotIn(title_after, description_before)
        project.title = title_after
        project.save()
        # nothing happens when CLI arg missing
        self._sync(project, update_description=False)
        description_after = self._get_entry_description(self._get_project_nonArchived_posixGroup_dn(project))
        self.assertIn(title_before, description_after)
        self.assertNotIn(title_after, description_after)
        # now something happens
        self._sync(project, update_description=True)
        description_after = self._get_entry_description(self._get_project_nonArchived_posixGroup_dn(project))
        self.assertNotIn(title_before, description_after)
        self.assertIn(title_after, description_after)
