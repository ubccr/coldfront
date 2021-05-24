import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
base_dir = settings.BASE_DIR

class Command(BaseCommand):

    def handle(self, *args, **options):
        admin_user, _ = get_user_model().objects.get_or_create(username='admin')
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()

        for user in get_user_model().objects.all():
            user.set_password('test1234')
            user.save()