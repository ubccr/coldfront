from io import StringIO

from django.core.management import call_command
from django.core.management import CommandError

from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.tests.test_billing_base import TestBillingBase
from coldfront.core.billing.utils import ProjectBillingActivityManager
from coldfront.core.billing.utils import ProjectUserBillingActivityManager
from coldfront.core.billing.utils import UserBillingActivityManager
from coldfront.core.billing.utils.queries import get_billing_activity_from_full_id
from coldfront.core.billing.utils.queries import is_billing_id_well_formed
from coldfront.core.billing.utils.validation import is_billing_id_valid
from coldfront.core.utils.tests.test_base import enable_deployment


class TestBillingIds(TestBillingBase):
    """A class for testing the billing_ids management command."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.command = BillingIdsCommand()

    def test_create_billing_id_existent(self):
        """Test that, when the given billing ID already exists, the
        'create' subcommand raises an error."""
        billing_id = '123456-788'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))

        _, error = self.command.create(billing_id)
        self.assertFalse(error)

        billing_activity = get_billing_activity_from_full_id(billing_id)
        self.assertTrue(isinstance(billing_activity, BillingActivity))

        with self.assertRaises(CommandError) as cm:
            self.command.create(billing_id)
        self.assertIn('already exists', str(cm.exception))

    def test_create_dry_run(self):
        """Test that, when the --dry_run flag is given to the 'create'
        subcommand, changes are displayed, but not performed."""
        billing_id = '123456-788'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))

        output, error = self.command.create(billing_id, dry_run=True)
        self.assertIn('Would create', output)
        self.assertFalse(error)

        self.assertIsNone(get_billing_activity_from_full_id(billing_id))

    def test_create_billing_id_invalid(self):
        """Test that, when the given billing ID is invalid, the 'create'
        subcommand raises an error, unless the --ignore_invalid flag is
        given, in which case a warning is raised before proceeding."""
        billing_id = '123456-789'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))
        self.assertFalse(is_billing_id_valid(billing_id))

        with self.assertRaises(CommandError) as cm:
            self.command.create(billing_id)
        self.assertIn('is invalid', str(cm.exception))

        output, error = self.command.create(billing_id, ignore_invalid=True)
        self.assertIn('is invalid', output)
        self.assertIn('Proceeding anyway', output)
        self.assertIn('Created', output)
        self.assertFalse(error)

        billing_activity = get_billing_activity_from_full_id(billing_id)
        self.assertTrue(isinstance(billing_activity, BillingActivity))

    def test_create_billing_id_malformed(self):
        """Test that, when the given billing ID is malformed, the
        'create' subcommand raises an error."""
        billing_id = '12345-67'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))
        self.assertFalse(is_billing_id_well_formed(billing_id))

        with self.assertRaises(CommandError) as cm:
            self.command.create(billing_id)
        self.assertIn('is malformed', str(cm.exception))

        self.assertIsNone(get_billing_activity_from_full_id(billing_id))

    def test_create_success(self):
        """Test that the 'create' subcommand successfully creates a
        billing ID."""
        billing_id = '123456-788'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))

        _, error = self.command.create(billing_id)
        self.assertFalse(error)

        billing_activity = get_billing_activity_from_full_id(billing_id)
        self.assertTrue(isinstance(billing_activity, BillingActivity))

    def test_set_billing_id_invalid(self):
        """Test that, when the given billing ID is invalid, each of the
        subcommands of the 'set' subcommand raises an error, unless the
        --ignore_invalid flag is given, in which case a warning is
        raised before proceeding."""
        billing_id = '123456-789'
        self.command.create(billing_id, ignore_invalid=True)

        billing_activity = get_billing_activity_from_full_id(billing_id)

        calls = [
            {
                'command': self.command.set_project_default,
                'manager': ProjectBillingActivityManager(self.project),
                'args': [self.project_name, billing_id],
            },
            {
                'command': self.command.set_recharge,
                'manager': ProjectUserBillingActivityManager(
                    self.project_user),
                'args': [self.project_name, self.user.username, billing_id],
            },
            {
                'command': self.command.set_user_account,
                'manager': UserBillingActivityManager(self.user),
                'args': [self.user.username, billing_id],
            }
        ]

        for call in calls:
            command = call['command']
            manager = call['manager']
            args = call['args']

            self.assertIsNone(manager.billing_activity)
            with self.assertRaises(CommandError) as cm:
                command(*args)
            self.assertIn('is invalid', str(cm.exception))
            self.assertIsNone(manager.billing_activity)

            output, error = command(*args, ignore_invalid=True)
            self.assertIn('is invalid', output)
            self.assertIn('Proceeding anyway', output)
            self.assertIn('Updated', output)
            self.assertFalse(error)

            self.assertEqual(manager.billing_activity, billing_activity)

    def test_set_billing_id_malformed(self):
        """Test that, when the given billing ID is malformed, each of
        the subcommands of the 'set' subcommand raises an error."""
        billing_id = '12345-67'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))
        self.assertFalse(is_billing_id_well_formed(billing_id))

        calls = [
            {
                'command': self.command.set_project_default,
                'manager': ProjectBillingActivityManager(self.project),
                'args': [self.project_name, billing_id],
            }
        ]

        for call in calls:
            command = call['command']
            manager = call['manager']
            args = call['args']

            self.assertIsNone(manager.billing_activity)
            with self.assertRaises(CommandError) as cm:
                command(*args)
            self.assertIn('is malformed', str(cm.exception))
            self.assertIsNone(manager.billing_activity)

    def test_set_billing_id_nonexistent(self):
        """Test that, when the given billing ID does not already exist,
        each of the subcommands of the 'set' subcommand raises an
        error."""
        billing_id = '123456-789'
        self.assertIsNone(get_billing_activity_from_full_id(billing_id))

        calls = [
            {
                'command': self.command.set_project_default,
                'manager': ProjectBillingActivityManager(self.project),
                'args': [self.project_name, billing_id],
            },
            {
                'command': self.command.set_recharge,
                'manager': ProjectUserBillingActivityManager(
                    self.project_user),
                'args': [self.project_name, self.user.username, billing_id],
            },
            {
                'command': self.command.set_user_account,
                'manager': UserBillingActivityManager(self.user),
                'args': [self.user.username, billing_id],
            }
        ]

        for call in calls:
            command = call['command']
            manager = call['manager']
            args = call['args']

            self.assertIsNone(manager.billing_activity)
            with self.assertRaises(CommandError) as cm:
                command(*args)
            self.assertIn('does not exist', str(cm.exception))
            self.assertIsNone(manager.billing_activity)

    def test_set_project_default_dry_run(self):
        """Test that, when the --dry_run flag is given to the
        'project_default' subcommand of the 'set' subcommand, changes
        are displayed, but not performed."""
        billing_id = '123456-788'
        self.command.create(billing_id)

        manager = ProjectBillingActivityManager(self.project)
        self.assertIsNone(manager.billing_activity)

        output, error = self.command.set_project_default(
            self.project_name, billing_id, dry_run=True)
        self.assertIn('Would update', output)
        self.assertFalse(error)

        self.assertIsNone(manager.billing_activity)

    def test_set_project_default_success(self):
        """Test that the 'project_default' subcommand of the 'set'
        subcommand successfully sets a billing ID for a Project."""
        billing_id = '123456-788'
        self.command.create(billing_id)
        billing_activity = get_billing_activity_from_full_id(billing_id)

        manager = ProjectBillingActivityManager(self.project)
        self.assertIsNone(manager.billing_activity)

        output, error = self.command.set_project_default(
            self.project_name, billing_id)
        self.assertIn('Updated', output)
        self.assertFalse(error)

        self.assertEqual(manager.billing_activity, billing_activity)

        other_billing_id = '123456-790'
        self.command.create(other_billing_id)
        other_billing_activity = get_billing_activity_from_full_id(
            other_billing_id)

        output, error = self.command.set_project_default(
            self.project_name, other_billing_id)
        self.assertIn('Updated', output)
        self.assertFalse(error)

        self.assertEqual(manager.billing_activity, other_billing_activity)

    def test_set_recharge_dry_run(self):
        """Test that, when the --dry_run flag is given to the 'recharge'
        subcommand of the 'set' subcommand, changes are displayed, but
        not performed."""
        billing_id = '123456-788'
        self.command.create(billing_id)

        manager = ProjectUserBillingActivityManager(self.project_user)
        self.assertIsNone(manager.billing_activity)

        output, error = self.command.set_recharge(
            self.project_name, self.user.username, billing_id, dry_run=True)
        self.assertIn('Would update', output)
        self.assertFalse(error)

        self.assertIsNone(manager.billing_activity)

    def test_set_recharge_success(self):
        """Test that the 'recharge' subcommand of the 'set' subcommand
        successfully sets a billing ID for a ProjectUser."""
        billing_id = '123456-788'
        self.command.create(billing_id)
        billing_activity = get_billing_activity_from_full_id(billing_id)

        manager = ProjectUserBillingActivityManager(self.project_user)
        self.assertIsNone(manager.billing_activity)

        output, error = self.command.set_recharge(
            self.project_name, self.user.username, billing_id)
        self.assertIn('Updated', output)
        self.assertFalse(error)

        self.assertEqual(manager.billing_activity, billing_activity)

        other_billing_id = '123456-790'
        self.command.create(other_billing_id)
        other_billing_activity = get_billing_activity_from_full_id(
            other_billing_id)

        output, error = self.command.set_recharge(
            self.project_name, self.user.username, other_billing_id)
        self.assertIn('Updated', output)
        self.assertFalse(error)

        self.assertEqual(manager.billing_activity, other_billing_activity)

    def test_set_user_account_dry_run(self):
        """Test that, when the --dry_run flag is given to the
        'user_account' subcommand of the 'set' subcommand, changes are
        displayed, but not performed."""
        billing_id = '123456-788'
        self.command.create(billing_id)

        manager = UserBillingActivityManager(self.user)
        self.assertIsNone(manager.billing_activity)

        output, error = self.command.set_user_account(
            self.user.username, billing_id, dry_run=True)
        self.assertIn('Would update', output)
        self.assertFalse(error)

        self.assertIsNone(manager.billing_activity)

    def test_set_user_account_success(self):
        """Test that the 'user_account' subcommand of the 'set'
        subcommand successfully sets a billing ID for a User."""
        billing_id = '123456-788'
        self.command.create(billing_id)
        billing_activity = get_billing_activity_from_full_id(billing_id)

        manager = UserBillingActivityManager(self.user)
        self.assertIsNone(manager.billing_activity)

        output, error = self.command.set_user_account(
            self.user.username, billing_id)
        self.assertIn('Updated', output)
        self.assertFalse(error)

        self.assertEqual(manager.billing_activity, billing_activity)

        other_billing_id = '123456-790'
        self.command.create(other_billing_id)
        other_billing_activity = get_billing_activity_from_full_id(
            other_billing_id)

        output, error = self.command.set_user_account(
            self.user.username, other_billing_id)
        self.assertIn('Updated', output)
        self.assertFalse(error)

        self.assertEqual(manager.billing_activity, other_billing_activity)


class BillingIdsCommand(object):
    """A wrapper class over the 'billing_ids' management command."""

    command_name = 'billing_ids'

    def call_subcommand(self, name, *args):
        """Call the subcommand with the given name and arguments. Return
        output written to stdout and stderr."""
        out, err = StringIO(), StringIO()
        args = [self.command_name, name, *args]
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()

    def create(self, billing_id, **flags):
        """Call the 'create' subcommand with the given billing ID, and
        flag values."""
        args = ['create', billing_id]
        self._add_flags_to_args(args, **flags)
        return self.call_subcommand(*args)

    def set_project_default(self, project_name, billing_id, **flags):
        """Call the 'project_default' subcommand of the 'set' subcommand
        with the given Project name, billing ID, and flag values."""
        args = ['set', 'project_default', project_name, billing_id]
        self._add_flags_to_args(args, **flags)
        return self.call_subcommand(*args)

    def set_recharge(self, project_name, username, billing_id, **flags):
        """Call the 'recharge' subcommand of the 'set' subcommand with
        the given Project name, username, billing ID, and flag
        values."""
        args = ['set', 'recharge', project_name, username, billing_id]
        self._add_flags_to_args(args, **flags)
        return self.call_subcommand(*args)

    def set_user_account(self, username, billing_id, **flags):
        """Call the 'user_account' subcommand of the 'set' subcommand
        with the given username, billing ID, and flag values."""
        args = ['set', 'user_account', username, billing_id]
        self._add_flags_to_args(args, **flags)
        return self.call_subcommand(*args)

    @staticmethod
    def _add_flags_to_args(args, **flags):
        """Given a list of arguments to the command and a dict of flag
        values, add the latter to the former."""
        for key in ('dry_run', 'ignore_invalid'):
            if flags.get(key, False):
                args.append(f'--{key}')
