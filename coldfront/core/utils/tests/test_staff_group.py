from django.test import TestCase

from django.contrib.auth.models import User, Group
from django.core.management import call_command

from io import StringIO
import os
import sys

class TestStaffGroup(TestCase):
    """ Test class to test that staff are created properly """

    def setUp(self):
        """Setup test data"""
        out, err = StringIO(), StringIO()
        commands = [
            'create_staff_group',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        self.password = 'password'

        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')

        self.staff1 = User.objects.create(
            email='staff1@email.com',
            first_name='Normal',
            last_name='Staff1',
            username='staff1')

    def test_staff_group_creation(self):
        self.assertTrue(Group.objects.filter(name='staff_group').exists())

        perm_codename_lst = [
            'view_allocationrenewalrequest',
            'view_vectorprojectallocationrequest',
            'view_savioprojectallocationrequest',
            'can_review_cluster_account_requests',
            'can_review_pending_project_reviews',
            'can_view_all_allocations',
            'can_view_all_projects',
        ]

        staff_group = Group.objects.get(name='staff_group')

        for codename in perm_codename_lst:
            self.assertTrue(staff_group.permissions.filter(codename=codename).exists())

    def test_give_staff_group(self):
        staff_group = Group.objects.get(name='staff_group')

        self.staff1.is_staff = True
        self.staff1.save()

        self.assertTrue(staff_group.user_set.filter(username=self.staff1.username).exists())
        self.assertTrue(self.staff1.groups.filter(name='staff_group').exists())

        self.assertFalse(staff_group.user_set.filter(username=self.user1.username).exists())
        self.assertFalse(self.user1.groups.filter(name='staff_group').exists())

    def test_remove_staff_group(self):
        staff_group = Group.objects.get(name='staff_group')

        self.staff1.is_staff = False
        self.staff1.save()

        self.assertFalse(staff_group.user_set.filter(username=self.staff1.username).exists())
        self.assertFalse(self.staff1.groups.filter(name='staff_group').exists())
