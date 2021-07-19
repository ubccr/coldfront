from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.project.models import Project
from coldfront.core.statistics.models import Job
from collections import defaultdict
from decimal import Decimal
from django.core.management.base import BaseCommand
import logging

"""An admin command that sets usages of 'Service Units' attributes based
on Jobs submitted since their respective start dates."""


class Command(BaseCommand):

    help = (
        'Set usages of "Service Units" attributes based on Jobs '
        'submitted since their respective start dates. This applies '
        'only to Savio Projects.')
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        prefixes = ('ac_', 'co_', 'fc_', 'ic_', 'pc_')
        projects = Project.objects.prefetch_related('projectuser_set')
        for project in projects.iterator():
            if not project.name.startswith(prefixes):
                continue
            allocation = Allocation.objects.prefetch_related(
                'allocationuser_set').filter(
                    resources__name='Savio Compute', project=project).first()
            start_date = allocation.start_date
            if not start_date:
                message = f'Project {project.pk} has no start date.'
                self.stderr.write(self.style.ERROR(message))
                self.logger.error(message)
                continue
            # Accumulate usages from Jobs submitted at or after the
            # allocation's start date.
            project_total = Decimal('0.00')
            project_user_totals = defaultdict(Decimal)
            for project_user in project.projectuser_set.all():
                project_user_totals[project_user.user.pk] = Decimal('0.00')
            jobs = Job.objects.filter(
                accountid=project, submitdate__gte=allocation.start_date)
            for job in jobs.iterator():
                project_total += job.amount
                project_user_totals[job.userid.pk] += job.amount
            # Set the Project's usage.
            # TODO: This will fail when more than one attribute has usage.
            try:
                allocation_attribute_usage = AllocationAttributeUsage.objects.get(
                    allocation_attribute__allocation=allocation.pk)
                allocation_attribute_usage.value = project_total
                allocation_attribute_usage.save()
                message = (
                    f'Set usage for Project {project.pk} to {project_total}.')
                self.stdout.write(self.style.SUCCESS(message))
                self.logger.info(message)
            except Exception as e:
                message = (
                    f'Failed to set usage for Project {project.pk} to '
                    f'{project_total}.')
                self.stderr.write(self.style.ERROR(message))
                self.logger.error(message)
                self.logger.exception(e)
            # Set the ProjectUsers' usages.
            for user_pk in project_user_totals:
                # TODO: This will fail when more than one attribute has usage.
                try:
                    amount = project_user_totals[user_pk]
                    allocation_user = allocation.allocationuser_set.get(
                        user__pk=user_pk)
                    allocation_user_attribute_usage = \
                        AllocationUserAttributeUsage.objects.get(
                            allocation_user_attribute__allocation_user=allocation_user)
                    allocation_user_attribute_usage.value = amount
                    allocation_user_attribute_usage.save()
                    message = (
                        f'Set usage for Project {project.pk} and User '
                        f'{user_pk} to {amount}.')
                    self.stdout.write(self.style.SUCCESS(message))
                    self.logger.info(message)
                except Exception as e:
                    message = (
                        f'Failed to set usage for Project {project.pk} and '
                        f'User {user_pk} to {amount}.')
                    self.stderr.write(self.style.ERROR(message))
                    self.logger.error(message)
                    self.logger.exception(e)
