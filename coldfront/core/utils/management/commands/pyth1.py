import datetime
import os
import csv

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)

def import_model_projects(filename):
    with open(filename) as file:
        f=csv.reader(file)
        for m in f:
            created, modified, title, pi_username, description, field_of_science, project_status, user_info = line.split(',')
            created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
            modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')
            pi_user_obj = User.objects.get(username=pi_username)
            pi_user_obj.is_pi = True
            pi_user_obj.save()
        for project_user in user_info.split(';'):
                    username, role, enable_email, project_user_status = project_user.split(',')
                    if enable_email == 'True':
                        enable_email = True
                    else:
                        enable_email = False
                    # print(username, role, enable_email, project_user_status)
                    user_obj = User.objects.get(username=username)
                    project_user_obj = ProjectUser.objects.create(
                        user=user_obj,
                        project=project_obj,
                        role=project_user_role_choices[role],
                        status=project_user_status_choices[project_user_status],
                        enable_notifications=enable_email
                    )
            
