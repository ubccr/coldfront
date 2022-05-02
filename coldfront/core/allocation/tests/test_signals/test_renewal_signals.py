from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime
from datetime import timedelta
from django.test import TestCase

from django_q.models import Schedule
from django_q.tasks import schedule


class TestAllocationPeriodSignals(TestCase):
    """Test that when AllocationPeriods are created, updated, and
    deleted, signals update ScheduledTasks for starting them."""

    def setUp(self):
        """Set up test data."""
        self.today = display_time_zone_current_date()
        self.started_period = AllocationPeriod(
            name='Period 1',
            start_date=self.today - timedelta(days=100),
            end_date=self.today + timedelta(days=100))
        self.non_started_period_1 = AllocationPeriod(
            name='Period 2',
            start_date=self.today + timedelta(days=1),
            end_date=self.today + timedelta(days=100))
        self.non_started_period_2 = AllocationPeriod(
            name='Period 3',
            start_date=self.today + timedelta(days=100),
            end_date=self.today + timedelta(days=200))

        self.func = 'django.core.management.call_command'
        self.command = 'start_allocation_period'

    def test_created_non_started_period_creates_tasks(self):
        """Test that when a non-started period is created, a task is
        scheduled."""
        # Create the period.
        self.non_started_period_1.save()

        # A task should have been created.
        all_tasks = Schedule.objects.all()
        self.assertEqual(all_tasks.count(), 1)
        created_task = all_tasks.first()
        self.assertEqual(created_task.func, self.func)
        self.assertEqual(
            created_task.args,
            f'(\'{self.command}\', {self.non_started_period_1.pk})')
        next_run = display_time_zone_date_to_utc_datetime(
            self.non_started_period_1.start_date)
        self.assertEqual(created_task.next_run, next_run)
        self.assertEqual(created_task.repeats, -1)
        self.assertEqual(created_task.schedule_type, Schedule.ONCE)

        # Creating a period should not reschedule tasks for other periods.
        self.non_started_period_2.save()
        self.assertEqual(Schedule.objects.count(), 2)

    def test_deleted_period_deletes_tasks(self):
        """Test that when a period is deleted, its corresponding tasks
        are deleted."""
        # Create periods.
        self.non_started_period_1.save()
        self.non_started_period_2.save()

        # There should be two tasks.
        all_tasks = Schedule.objects.order_by('id')
        self.assertEqual(all_tasks.count(), 2)
        self.period_1_task = all_tasks.first()
        self.period_2_task = all_tasks.last()

        # Delete the first, which should delete its task.
        self.non_started_period_1.delete()
        try:
            Schedule.objects.get(pk=self.period_1_task.pk)
        except Schedule.DoesNotExist:
            pass
        else:
            self.fail(
                f'Schedule {self.period_1_task.pk} should have been deleted.')

        # Delete the second, which should delete its task.
        self.non_started_period_2.delete()
        try:
            Schedule.objects.get(pk=self.period_2_task.pk)
        except Schedule.DoesNotExist:
            pass
        else:
            self.fail(
                f'Schedule {self.period_2_task.pk} should have been deleted.')

    def test_started_period_ignored(self):
        """Test that when a started period is created or updated, existing
        tasks are deleted, but no new ones are scheduled."""
        # Create the period.
        self.started_period.save()

        # No task should have been scheduled.
        self.assertEqual(Schedule.objects.count(), 0)

        # Create one manually.
        next_run = display_time_zone_date_to_utc_datetime(
            self.started_period.start_date)
        kwargs = {
            'next_run': next_run,
            'repeats': -1,
            'schedule_type': Schedule.ONCE,
        }
        schedule(self.func, self.command, self.started_period.pk, **kwargs)
        self.assertEqual(Schedule.objects.count(), 1)

        # Update the period.
        self.started_period.save()

        # The task should be deleted, and no new one should have been
        # scheduled.
        self.assertEqual(Schedule.objects.count(), 0)

    def test_updated_non_started_period_reschedules_tasks(self):
        """Test that when a non-started period is updated, existing
        tasks for that period are deleted and a new one is scheduled."""
        # Create the period.
        self.non_started_period_1.save()
        all_tasks = Schedule.objects.all()
        self.assertEqual(all_tasks.count(), 1)
        created_task = all_tasks.first()

        # Update the period.
        self.non_started_period_1.save()

        # The existing ScheduledTask should have been deleted, and a new one
        # should have been created.
        try:
            Schedule.objects.get(pk=created_task.pk)
        except Schedule.DoesNotExist:
            pass
        else:
            self.fail(f'Schedule {created_task.pk} should have been deleted.')
        all_tasks = Schedule.objects.all()
        self.assertEqual(all_tasks.count(), 1)
        updated_task = all_tasks.first()

        # Create and updating a period should not reschedule tasks for other
        # periods.
        for i in range(2):
            self.non_started_period_2.save()
            try:
                Schedule.objects.get(pk=updated_task.pk)
            except Schedule.DoesNotExist:
                self.fail(
                    f'Schedule {updated_task.pk} should not have been '
                    f'deleted.')
            self.assertEqual(Schedule.objects.count(), 2)
