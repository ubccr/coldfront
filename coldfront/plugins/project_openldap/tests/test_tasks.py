# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
import string
from unittest.mock import patch

from coldfront.core.test_helpers.factories import (
    ProjectUserRoleChoiceFactory,
    UserFactory,
)
from coldfront.plugins.project_openldap import tasks

from . import ProjectOpenLdapTestCase


class TasksTest(ProjectOpenLdapTestCase):
    gid_start = 8000

    def setUp(self):
        ProjectOpenLdapTestCase._setUp(self)
        self._setUp(self.gid_start)

    def test_create(self):
        project = self._create_project_with_members([])
        tasks.add_project(project)
        self.assertTrue(self._does_entry_exist(self._get_project_nonArchived_ou_dn(project), "organizationalUnit"))
        self.assertTrue(self._does_entry_exist(self._get_project_nonArchived_posixGroup_dn(project), "posixGroup"))
        self.assertIn(
            project.pi.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project))
        )
        self.assertEqual(
            self._get_entry_gidNumber(self._get_project_nonArchived_posixGroup_dn(project)), project.pk + self.gid_start
        )

    def test_delete(self):
        project = self._create_project_with_members([])
        tasks.add_project(project)
        with (
            patch.object(tasks, "PROJECT_OPENLDAP_REMOVE_PROJECT", True),
            patch.object(tasks, "PROJECT_OPENLDAP_ARCHIVE_OU", ""),
        ):
            tasks.remove_project(project)
        self.assertFalse(self._does_entry_exist(self._get_project_nonArchived_posixGroup_dn(project), "posixGroup"))
        self.assertFalse(self._does_entry_exist(self._get_project_nonArchived_ou_dn(project), "organizationalUnit"))

    def test_archive(self):
        project = self._create_project_with_members([])
        tasks.add_project(project)
        with (
            patch.object(tasks, "PROJECT_OPENLDAP_REMOVE_PROJECT", False),
            patch.object(tasks, "PROJECT_OPENLDAP_ARCHIVE_OU", self.archived_projects_ou),
            patch("coldfront.plugins.project_openldap.utils.PROJECT_OPENLDAP_ARCHIVE_OU", self.archived_projects_ou),
        ):
            tasks.remove_project(project)
        self.assertFalse(self._does_entry_exist(self._get_project_nonArchived_ou_dn(project), "organizationalUnit"))
        self.assertTrue(self._does_entry_exist(self._get_project_archived_ou_dn(project), "organizationalUnit"))

    def test_add_member_uid(self):
        project = self._create_project_with_members([])
        user = UserFactory()
        tasks.add_project(project)
        self.assertNotIn(user.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project)))
        project.add_user(user, ProjectUserRoleChoiceFactory())
        project.save()
        tasks.add_user_project(user.pk)
        self.assertIn(user.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project)))

    def test_remove_member_uid(self):
        user = UserFactory()
        project = self._create_project_with_members([user.username])
        projectuser_pk = project.projectuser_set.get(user=user).pk
        tasks.add_project(project)
        # for some reason add_project will only add the PI to the posixgroup
        tasks.add_user_project(projectuser_pk)
        self.assertTrue(self._is_user_in_nonArchived_ldap_group(user, project))
        self.assertIn(user.username, self._get_entry_memberUid(self._get_project_nonArchived_posixGroup_dn(project)))
        project.remove_user(user)
        project.save()
        tasks.remove_user_project(projectuser_pk)
        self.assertFalse(self._is_user_in_nonArchived_ldap_group(user, project))

    def test_update_posixGroup_description(self):
        title_after = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        project = self._create_project_with_members([])
        tasks.add_project(project)
        description_before = self._get_entry_description(self._get_project_nonArchived_posixGroup_dn(project))
        title_before = project.title
        self.assertIn(title_before, description_before)
        self.assertNotIn(title_after, description_before)
        project.title = title_after
        project.save()
        tasks.update_project(project)
        description_after = self._get_entry_description(self._get_project_nonArchived_posixGroup_dn(project))
        self.assertNotIn(title_before, description_after)
        self.assertIn(title_after, description_after)
