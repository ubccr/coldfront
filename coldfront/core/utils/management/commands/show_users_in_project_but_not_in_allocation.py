import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from coldfront.core.project.models import Project

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        for project in Project.objects.filter(status__name__in=['Active', 'New']):
            users_in_project = list(project.projectuser_set.filter(
                status__name='Active').values_list('user__username', flat=True))
            users_in_allocation = []
            for allocation in project.allocation_set.filter(status__name__in=('Active',
                                                                              'New', 'Paid', 'Payment Pending',
                                                                              'Payment Requested', 'Renewal Requested')):

                users_in_allocation.extend(allocation.allocationuser_set.filter(
                    status__name='Active').values_list('user__username', flat=True))

            extra_users = list(set(users_in_project)-set(users_in_allocation))
            if extra_users:
                pi_usernames = ', '.join([pi.username for pi in project.pis()])
                print(project.id, project.title, pi_usernames, extra_users)
