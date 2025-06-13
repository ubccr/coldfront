from coldfront.core.project.models import (
    ProjectUserRoleChoice,
    ProjectUser,
    ProjectUserStatusChoice,
)
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
import datetime

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationAttributeType,
    AllocationAttribute,
    AttributeType,
)
from coldfront.core.allocation.tasks import (
    send_expiring_mails,
    send_expired_mails,
    send_expiry_emails,
)
from coldfront.core.test_helpers.factories import (
    SchoolFactory,
    ProjectStatusChoiceFactory,
    ProjectFactory,
    UserFactory,
    ResourceFactory,
)
from coldfront.core.user.models import UserProfile, ApproverProfile


class SendExpiryEmailsWrapperTest(TestCase):
    @patch("coldfront.core.allocation.tasks.send_expired_mails")
    @patch("coldfront.core.allocation.tasks.send_expiring_mails")
    def test_send_expiry_emails_calls_both_functions(self, mock_expiring, mock_expired):
        send_expiry_emails()

        mock_expiring.assert_called_once()
        mock_expired.assert_called_once()


class SendExpiringMailsTest(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        self.target_date = self.today + datetime.timedelta(days=3)

        # Create schools
        self.school = SchoolFactory(description="Tandon School of Engineering")
        self.school2 = SchoolFactory(description="NYU IT")

        # Approver for correct school
        self.approver_mail = "approver@example.com"
        self.approver_user = UserFactory(username="approver1", email=self.approver_mail)
        self.approver_user_profile = UserProfile.objects.get(user=self.approver_user)
        self.approver_profile = ApproverProfile.objects.create(
            user_profile=self.approver_user_profile
        )
        self.approver_profile.schools.add(self.school)

        # Approver for unrelated school
        self.other_approver_mail = "approver2@example.com"
        self.other_user = UserFactory(
            username="approver2", email=self.other_approver_mail
        )
        self.other_user_profile = UserProfile.objects.get(user=self.other_user)
        self.other_approver_profile = ApproverProfile.objects.create(
            user_profile=self.other_user_profile
        )
        self.other_approver_profile.schools.add(self.school2)

        # PI and Project
        self.pi = UserFactory(username="pi1", email="pi@example.com")
        self.project = ProjectFactory(
            title="Test Project",
            pi=self.pi,
            status=ProjectStatusChoiceFactory(name="Active"),
            school=self.school,
        )

        # Allocation
        self.status, _ = AllocationStatusChoice.objects.get_or_create(name="Active")
        self.resource = ResourceFactory(name="Tandon-GPU-Adv", school=self.school)
        self.allocation = Allocation.objects.create(
            project=self.project, status=self.status, end_date=self.target_date
        )
        self.allocation.resources.set([self.resource])
        self.attribute_type, _ = AttributeType.objects.get_or_create(name="Yes/No")

        self.expire_attr_type = AllocationAttributeType.objects.create(
            name="EXPIRE NOTIFICATION",
            attribute_type=self.attribute_type,
            has_usage=False,
            is_private=True,
        )
        self.cloud_attr_type = AllocationAttributeType.objects.create(
            name="CLOUD USAGE NOTIFICATION",
            attribute_type=self.attribute_type,
            has_usage=False,
            is_private=True,
        )

        AllocationAttribute.objects.create(
            allocation=self.allocation,
            allocation_attribute_type=self.expire_attr_type,
            value="Yes",
        )
        AllocationAttribute.objects.create(
            allocation=self.allocation,
            allocation_attribute_type=self.cloud_attr_type,
            value="Yes",
        )

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
        new=[3],
    )
    def test_emails_sent_to_approver_and_pi(self, mock_send_email):
        send_expiring_mails()

        # Should be 2 calls: one to approver, one to PI
        self.assertEqual(mock_send_email.call_count, 2)

        recipients = []
        for call in mock_send_email.call_args_list:
            args, kwargs = call
            recipients += args[-1]  # recipient

        self.assertIn(self.approver_mail, recipients)
        self.assertIn(self.pi.email, recipients)
        self.assertNotIn(self.other_approver_mail, recipients)

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
        new=[3],
    )
    def test_allocation_not_expiring_soon_does_not_trigger_email(self, mock_send_email):
        # Change allocation to expire in 10 days (not in EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)
        self.allocation.end_date = self.today + datetime.timedelta(days=10)
        self.allocation.save()
        send_expiring_mails()
        mock_send_email.assert_not_called()

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
        new=[3],
    )
    def test_no_email_if_expire_notification_is_no(self, mock_send_email):
        AllocationAttribute.objects.filter(
            allocation=self.allocation, allocation_attribute_type=self.expire_attr_type
        ).update(value="No")

        send_expiring_mails()
        mock_send_email.assert_not_called()

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
        new=[3],
    )
    def test_no_email_if_cloud_usage_notification_is_no(self, mock_send_email):
        AllocationAttribute.objects.filter(
            allocation=self.allocation, allocation_attribute_type=self.cloud_attr_type
        ).update(value="No")

        send_expiring_mails()
        mock_send_email.assert_not_called()

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
        new=[3],
    )
    def test_only_correct_school_approver_gets_email(self, mock_send_email):
        send_expiring_mails()

        recipients = []
        for call in mock_send_email.call_args_list:
            args, kwargs = call
            recipients += args[-1]  # recipient

        self.assertIn(self.approver_mail, recipients)
        self.assertNotIn(self.other_approver_mail, recipients)

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
        new=[3],
    )
    def test_project_manager_receives_email(self, mock_send_email):
        # Create a project manager
        manager_email = "manager@example.com"
        manager_user = UserFactory(username="manager1", email=manager_email)

        # Assign 'Manager' role and 'Active' status to the user
        manager_role = ProjectUserRoleChoice.objects.create(name="Manager")
        active_status = ProjectUserStatusChoice.objects.create(name="Active")

        ProjectUser.objects.create(
            user=manager_user,
            project=self.project,
            role=manager_role,
            status=active_status,
        )

        # Send notification emails
        send_expiring_mails()

        # Extract recipient emails
        recipients = []
        for call in mock_send_email.call_args_list:
            args, kwargs = call
            recipients += args[-1]  # recipient email(s)

        self.assertIn(manager_email, recipients)
        self.assertIn(self.approver_mail, recipients)
        self.assertIn(self.pi.email, recipients)


class SendExpiredMailsTest(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        self.expired_date = self.today - datetime.timedelta(days=1)

        # Schools
        self.school = SchoolFactory(description="Tandon School of Engineering")
        self.school2 = SchoolFactory(description="NYU IT")

        # Approver with correct school
        self.approver_mail = "approver@example.com"
        self.approver_user = UserFactory(username="approver1", email=self.approver_mail)
        self.approver_user_profile = UserProfile.objects.get(user=self.approver_user)
        self.approver_profile = ApproverProfile.objects.create(
            user_profile=self.approver_user_profile
        )
        self.approver_profile.schools.add(self.school)

        # Approver with unrelated school
        self.other_approver_mail = "approver2@example.com"
        self.other_user = UserFactory(
            username="approver2", email=self.other_approver_mail
        )
        self.other_user_profile = UserProfile.objects.get(user=self.other_user)
        self.other_approver_profile = ApproverProfile.objects.create(
            user_profile=self.other_user_profile
        )
        self.other_approver_profile.schools.add(self.school2)

        # PI and Project
        self.pi = UserFactory(username="pi1", email="pi@example.com")
        self.project = ProjectFactory(
            title="Test Project",
            pi=self.pi,
            status=ProjectStatusChoiceFactory(name="Active"),
            school=self.school,
        )

        # Allocation
        self.status, _ = AllocationStatusChoice.objects.get_or_create(name="Active")
        self.resource = ResourceFactory(name="Tandon-GPU-Adv", school=self.school)
        self.allocation = Allocation.objects.create(
            project=self.project,
            status=self.status,
            end_date=self.expired_date,
        )
        self.allocation.resources.set([self.resource])

        # Attributes
        self.attribute_type, _ = AttributeType.objects.get_or_create(name="Yes/No")
        self.expire_attr_type = AllocationAttributeType.objects.create(
            name="EXPIRE NOTIFICATION",
            attribute_type=self.attribute_type,
            has_usage=False,
            is_private=True,
        )
        self.cloud_attr_type = AllocationAttributeType.objects.create(
            name="CLOUD USAGE NOTIFICATION",
            attribute_type=self.attribute_type,
            has_usage=False,
            is_private=True,
        )

        AllocationAttribute.objects.create(
            allocation=self.allocation,
            allocation_attribute_type=self.expire_attr_type,
            value="Yes",
        )

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ADMINS_ON_ALLOCATION_EXPIRE", new=False
    )
    def test_emails_sent_to_approver_and_pi_on_expiry(self, mock_send_email):
        send_expired_mails()

        self.assertEqual(mock_send_email.call_count, 2)  # PI + Approver

        recipients = []
        for call in mock_send_email.call_args_list:
            args, _ = call
            recipients += args[-1]

        self.assertIn(self.approver_mail, recipients)
        self.assertIn(self.pi.email, recipients)
        self.assertNotIn(self.other_approver_mail, recipients)

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ADMINS_ON_ALLOCATION_EXPIRE", new=False
    )
    def test_allocation_not_expired_does_not_trigger_email(self, mock_send_email):
        self.allocation.end_date = self.today  # Not expired
        self.allocation.save()
        send_expired_mails()
        mock_send_email.assert_not_called()

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ADMINS_ON_ALLOCATION_EXPIRE", new=False
    )
    def test_no_email_if_expire_notification_is_no(self, mock_send_email):
        AllocationAttribute.objects.filter(
            allocation=self.allocation, allocation_attribute_type=self.expire_attr_type
        ).update(value="No")

        send_expired_mails()
        mock_send_email.assert_not_called()

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ADMINS_ON_ALLOCATION_EXPIRE", new=False
    )
    def test_only_correct_school_approver_gets_email(self, mock_send_email):
        send_expired_mails()

        recipients = []
        for call in mock_send_email.call_args_list:
            args, _ = call
            recipients += args[-1]

        self.assertIn(self.approver_mail, recipients)
        self.assertNotIn(self.other_approver_mail, recipients)

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ADMINS_ON_ALLOCATION_EXPIRE", new=True
    )
    def test_admin_summary_email_sent(self, mock_send_email):
        send_expired_mails()

        # Should include: 2 user emails + 1 admin summary
        self.assertEqual(mock_send_email.call_count, 3)

        subjects = [call.args[0] for call in mock_send_email.call_args_list]
        self.assertIn("Allocation(s) have expired", subjects)

    @patch("coldfront.core.allocation.tasks.send_email_template")
    @patch(
        "coldfront.core.allocation.tasks.EMAIL_ADMINS_ON_ALLOCATION_EXPIRE", new=True
    )
    def test_project_manager_receives_email(self, mock_send_email):
        # Create a project manager
        manager_email = "manager@example.com"
        manager_user = UserFactory(username="manager1", email=manager_email)

        # Assign 'Manager' role and 'Active' status to the user
        manager_role = ProjectUserRoleChoice.objects.create(name="Manager")
        active_status = ProjectUserStatusChoice.objects.create(name="Active")

        ProjectUser.objects.create(
            user=manager_user,
            project=self.project,
            role=manager_role,
            status=active_status,
        )

        # Send notification emails
        send_expired_mails()

        # Extract recipient emails
        recipients = []
        for call in mock_send_email.call_args_list:
            args, kwargs = call
            recipients += args[-1]  # recipient email(s)

        self.assertIn(manager_email, recipients)
        self.assertIn(self.approver_mail, recipients)
        self.assertIn(self.pi.email, recipients)
