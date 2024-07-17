from django.core import mail
from django.test import TestCase, override_settings
from smtplib import SMTPException
from unittest import mock, skip
from unittest.mock import patch, MagicMock

from coldfront.core.utils.mail import (
    send_email,
    send_email_template,
    email_template_context,
    send_allocation_admin_email,
    send_allocation_customer_email,
    CENTER_BASE_URL,
    build_link,
    logger
)

@patch('coldfront.core.utils.mail.EMAIL_ENABLED', True)
@patch('coldfront.config.email.EMAIL_BACKEND', 'django.core.mail.backends.locmem.EmailBackend')
@patch('coldfront.core.utils.mail.EMAIL_SENDER', 'test-admin@coldfront.org')
@patch('coldfront.core.utils.mail.EMAIL_TICKET_SYSTEM_ADDRESS', 'tickets@example.org')
class EmailFunctionsTestCase(TestCase):

    def setUp(self):
        self.subject = 'Test Subject'
        self.body = 'Test Body'
        self.sender = 'sender@example.com'
        self.receiver_list = ['receiver@example.com']
        self.cc_list = ['cc@example.com']
        self.template_name = 'email/test_email_template.html'
        self.template_context = {'test_key': 'test_value'}

    @override_settings(EMAIL_ENABLED=False)
    def test_send_email_not_enabled(self):
        with patch('coldfront.core.utils.mail.EMAIL_ENABLED', False):
            send_email(self.subject, self.body, self.sender, self.receiver_list, self.cc_list)
            self.assertEqual(len(mail.outbox), 0)

    @skip('Fails for logging-related reason during GitHub Actions CI/CD pipeline')
    def test_send_email_missing_receiver_list(self):
        print('test_send_email_missing_receiver_list')
        with self.assertLogs(logger, level='ERROR') as log:
            send_email(self.subject, self.body, self.sender, [], self.cc_list)
            print([message for message in log.output])
            self.assertTrue(any('Failed to send email missing receiver_list' in message for message in log.output))
        self.assertEqual(len(mail.outbox), 0)

    @skip('Fails for logging-related reason during GitHub Actions CI/CD pipeline')
    def test_send_email_missing_sender(self):
        print('test_send_email_missing_sender')
        with self.assertLogs(logger, level='ERROR') as log:
            send_email(self.subject, self.body, '', self.receiver_list, self.cc_list)
            print("test_send_email_missing_sender log.output: ", [message for message in log.output])
            print("test_send_email_missing_sender mail.outbox: ", mail.outbox)
            self.assertTrue(any('Failed to send email missing sender address' in message for message in log.output))
        self.assertEqual(len(mail.outbox), 0)

    @patch('coldfront.core.utils.mail.EMAIL_SUBJECT_PREFIX', '[PREFIX]')
    def test_send_email_with_subject_prefix(self):#, mock_send):
        send_email(self.subject, self.body, self.sender, self.receiver_list, self.cc_list)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[PREFIX] Test Subject')

    @override_settings(DEBUG=True)
    @patch('coldfront.core.utils.mail.EMAIL_DEVELOPMENT_EMAIL_LIST', ['dev@example.com'])
    def test_send_email_in_debug_mode(self):
        send_email(self.subject, self.body, self.sender, self.receiver_list, self.cc_list)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['dev@example.com'])
        self.assertEqual(mail.outbox[0].cc, ['dev@example.com'])

    @patch('coldfront.core.utils.mail.EMAIL_SUBJECT_PREFIX', '[ColdFront]')
    def test_send_email_success(self):
        send_email(self.subject, self.body, self.sender, self.receiver_list, self.cc_list)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[ColdFront] Test Subject')
        self.assertEqual(mail.outbox[0].body, 'Test Body')
        self.assertEqual(mail.outbox[0].from_email, self.sender)
        self.assertEqual(mail.outbox[0].to, self.receiver_list)
        self.assertEqual(mail.outbox[0].cc, self.cc_list)

    @skip('Fails for logging-related reason during GitHub Actions CI/CD pipeline')
    @patch('coldfront.core.utils.mail.EMAIL_SUBJECT_PREFIX', '[ColdFront]')
    @patch('coldfront.core.utils.mail.EmailMessage.send', side_effect=SMTPException)
    def test_send_email_smtp_exception(self, mock_send):
        with self.assertLogs(logger, level='ERROR') as log:
            send_email(self.subject, self.body, self.sender, self.receiver_list, self.cc_list)
            self.assertTrue(any('Failed to send email to receiver@example.com from sender@example.com with subject [ColdFront] Test Subject' in message for message in log.output))
        self.assertEqual(len(mail.outbox), 0)
        mock_send.assert_called_once()

    def test_send_email_template(self):
        send_email_template(self.subject, self.template_name, self.template_context, self.sender, self.receiver_list, self.cc_list)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body, 'Rendered Body\n')

    def test_email_template_context(self):
        context = email_template_context()
        self.assertIn('center_name', context)
        self.assertIn('signature', context)
        self.assertIn('opt_out_instruction_url', context)

    def test_build_link(self):
        url_path = '/test-path/'
        domain_url = 'https://example.com'
        expected_url = f'{domain_url}{url_path}'
        self.assertEqual(build_link(url_path, domain_url), expected_url)
        self.assertEqual(build_link(url_path), f'{CENTER_BASE_URL}{url_path}')

    def test_send_allocation_admin_email(self):
        allocation_obj = MagicMock()
        allocation_obj.project.pi.first_name = 'John'
        allocation_obj.project.pi.last_name = 'Doe'
        allocation_obj.project.pi.username = 'jdoe'
        allocation_obj.get_parent_resource = 'Test Resource'
        send_allocation_admin_email(allocation_obj, self.subject, self.template_name)
        self.assertEqual(len(mail.outbox), 1)

    @patch('coldfront.core.utils.mail.reverse', return_value='/test-path/')
    @patch('coldfront.core.utils.mail.render_to_string', return_value='Rendered Body')
    def test_send_allocation_customer_email(self, mock_render, mock_reverse):
        allocation_obj = MagicMock()
        allocation_obj.pk = 1
        allocation_obj.get_parent_resource = 'Test Resource'
        allocation_user = MagicMock()
        allocation_user.user.email = 'user@example.com'
        allocation_user.allocation.project.projectuser_set.get.return_value.enable_notifications = True
        allocation_obj.allocationuser_set.exclude.return_value = [allocation_user]
        send_allocation_customer_email(allocation_obj, self.subject, self.template_name)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('user@example.com', mail.outbox[0].to)
        mock_render.assert_called_once_with(self.template_name, mock.ANY)
