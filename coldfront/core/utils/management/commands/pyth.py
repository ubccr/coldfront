import os
import csv

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

def import_model(filename):
    with open(filename) as file:
        next(file)
        f=csv.reader(file)
        for m in f:
            username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups = m
            user_obj = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=is_active,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

            if groups:
                groups = groups[0]
            else:
                groups = ''
            user_obj.save()
            # print(first_name," complete")
import_model('sample_csv.csv')
