import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        call_command('loaddata', 'dummy_data.json')
        for user in User.objects.all():
            user.set_password('test1234')
            user.save()

        print('All user passwords are set to "test1234", including user "admin".')
