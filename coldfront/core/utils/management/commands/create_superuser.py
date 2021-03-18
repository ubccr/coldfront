import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
base_dir = settings.BASE_DIR

class Command(BaseCommand):

    def handle(self, *args, **options):
        admin_user, _ = User.objects.get_or_create(username='admin')
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()

        for user in User.objects.all():
            user.set_password('test1234')
            user.save()