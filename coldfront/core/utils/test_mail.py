from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.core.test_helpers.factories import SchoolFactory, ProjectStatusChoiceFactory, \
    ProjectFactory, UserFactory, ResourceFactory
from coldfront.core.utils.mail import send_allocation_admin_email, send_admin_email_template, EMAIL_SENDER, \
    EMAIL_TICKET_SYSTEM_ADDRESS
from coldfront.core.user.models import UserProfile, ApproverProfile
from django.test import TestCase
from unittest.mock import patch
import datetime


class EmailUtilsTests(TestCase):

    @patch('coldfront.core.utils.mail.send_email_template')
    def test_send_admin_email_template_with_receiver(self, mock_send_email_template):
        context = {'pi': 'Test PI', 'resource': 'Test Resource', 'url': 'https://example.com'}
        receivers = ['admin@example.com']
        send_admin_email_template('Test Subject', 'template.txt', context, receiver_list=receivers)

        mock_send_email_template.assert_called_once_with(
            'Test Subject', 'template.txt', context, EMAIL_SENDER, receivers
        )

    @patch('coldfront.core.utils.mail.send_email_template')
    def test_send_admin_email_template_with_default_receiver(self, mock_send_email_template):
        context = {'pi': 'Test PI', 'resource': 'Test Resource', 'url': 'https://example.com'}
        send_admin_email_template('Test Subject', 'template.txt', context)

        mock_send_email_template.assert_called_once_with(
            'Test Subject', 'template.txt', context, EMAIL_SENDER, [EMAIL_TICKET_SYSTEM_ADDRESS, ]
        )


class SendAllocationAdminEmailTests(TestCase):

    def setUp(self):
        # approver with allocation's school
        self.school = SchoolFactory(description='Tandon School of Engineering')
        self.approver_mail = 'approver@example.com'
        self.user = UserFactory(username='approver1', email=self.approver_mail)
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.approver_profile = ApproverProfile.objects.create(user_profile=self.user_profile)
        self.approver_profile.schools.add(self.school)
        # approver with another school
        self.school2 = SchoolFactory(description='NYU IT')
        self.other_school_approver_mail = 'approver2@example.com'
        self.other_school_user = UserFactory(username='other_school_approver', email=self.other_school_approver_mail)
        self.other_school_user_profile = UserProfile.objects.get(user=self.other_school_user)
        self.other_school_approver_profile = ApproverProfile.objects.create(user_profile=self.other_school_user_profile)
        self.other_school_approver_profile.schools.add(self.school2)

        self.pi = UserFactory(username='pi1', first_name='Alice', last_name='Wong')
        self.project = ProjectFactory(title='Test Project', pi=self.pi, status=ProjectStatusChoiceFactory(name='Active'), school=self.school)
        self.status, _ = AllocationStatusChoice.objects.get_or_create(name='Active')
        self.resource = ResourceFactory(name="Tandon-GPU-Adv", school=self.school)
        self.allocation = Allocation.objects.create(
            project=self.project,
            status=self.status,
            end_date=datetime.date(2030, 1, 1),
        )
        self.allocation.resources.set([self.resource])

    @patch('coldfront.core.utils.mail.send_admin_email_template')
    def test_send_allocation_admin_email_sends_to_matching_approvers(self, mock_send):
        mock_link = 'https://example.com'
        with patch('coldfront.core.utils.mail.build_link', return_value=mock_link):
            with patch('coldfront.core.utils.mail.email_template_context', return_value={}):
                send_allocation_admin_email(self.allocation, 'Test Subject', 'template.txt')

        mock_send.assert_called_once()
        call_args, call_kwargs = mock_send.call_args
        template_context = call_args[2]
        recipients = call_kwargs.get('receiver_list')
        self.assertEqual([self.approver_mail], recipients)
        self.assertEqual(template_context['pi'], f'{self.pi.first_name} {self.pi.last_name} ({self.pi.username})')
        self.assertEqual(template_context['resource'], self.resource)
        self.assertEqual(template_context['url'], mock_link)

    @patch('coldfront.core.utils.mail.send_admin_email_template')
    def test_send_allocation_admin_email_skips_if_no_matching_approvers(self, mock_send):
        self.approver_profile.schools.clear()  # Remove school mapping
        mock_link = 'https://example.com'

        with patch('coldfront.core.utils.mail.build_link', return_value=mock_link):
            with patch('coldfront.core.utils.mail.email_template_context', return_value={}):
                send_allocation_admin_email(self.allocation, 'Test Subject', 'template.txt')

        mock_send.assert_not_called()
