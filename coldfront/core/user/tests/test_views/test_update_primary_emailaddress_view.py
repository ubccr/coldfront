from coldfront.core.user.models import EmailAddress
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse


class TestUpdateUserPrimaryEmailAddress(TestCase):
    """
    A class for testing the view for updating a user's
    primary email address'.
    """

    def setUp(self):
        """Set up test data."""
        self.password = 'password'

        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='First',
            last_name='Last',
            username='user1')
        self.user1.set_password(self.password)
        self.user1.save()

        self.email1 = EmailAddress.objects.create(
            user=self.user1,
            email='email1@email.com',
            is_verified=True,
            is_primary=True)

        self.email2 = EmailAddress.objects.create(
            user=self.user1,
            email='email2@email.com',
            is_verified=True,
            is_primary=False)

        self.client = Client()

    def test_update_primary_emailaddress_view(self):
        """
        Testing UpdatePrimaryEmailAddressView
        """

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'update-primary-email-address')
        data = {'email_address': str(self.email2.pk)}
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Your current primary email address '
                                      f'is: {self.email1.email}.')
        self.assertContains(response, self.email2.email)

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        self.email1.refresh_from_db()
        self.email2.refresh_from_db()

        self.assertTrue(self.email2.is_primary)
        self.assertFalse(self.email1.is_primary)

        self.assertRedirects(response, reverse('user-profile'))

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(len(messages), 1)
        self.assertEqual(messages[0], f'{self.email2.email} is your new '
                                      f'primary email address.')

        self.client.logout()
