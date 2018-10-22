import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding projects ...')
        delimiter = chr(255)
        file_path = os.path.join(base_dir, 'local_data', 'project_and_associated_users.tsv')
        Project.objects.all().delete()
        ProjectUser.objects.all().delete()

        project_status_choices = {}
        project_status_choices['Active'] = ProjectStatusChoice.objects.get(name='Active')
        project_status_choices['Archived'] = ProjectStatusChoice.objects.get(name='Archived')
        project_status_choices['New'] = ProjectStatusChoice.objects.get(name='New')

        project_user_role_choices = {}
        project_user_role_choices['PI'] = ProjectUserRoleChoice.objects.get(name='Manager')
        project_user_role_choices['U'] = ProjectUserRoleChoice.objects.get(name='User')
        project_user_role_choices['M'] = ProjectUserRoleChoice.objects.get(name='Manager')
        project_user_role_choices['Manager'] = ProjectUserRoleChoice.objects.get(name='Manager')

        project_user_status_choices = {}
        project_user_status_choices['ACT'] = ProjectUserStatusChoice.objects.get(name='Active')
        project_user_status_choices['PEA'] = ProjectUserStatusChoice.objects.get(name='Pending - Add')
        project_user_status_choices['PER'] = ProjectUserStatusChoice.objects.get(name='Pending - Remove')
        project_user_status_choices['DEN'] = ProjectUserStatusChoice.objects.get(name='Denied')
        project_user_status_choices['REM'] = ProjectUserStatusChoice.objects.get(name='Removed')
        project_user_status_choices['Missing'] = ProjectUserStatusChoice.objects.get(name='Removed')

        for choice in ['Active', 'Pending Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        with open(file_path, 'r') as fp:
            lines = fp.read().split('$$$$$$$$$$-new-line-$$$$$$$$$$')
            for idx, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    continue

                created, modified, title, pi_username, description, field_of_science, project_status, user_info = line.split(delimiter)
                # print(title, pi_username, description, field_of_science, project_status, user_info)

                created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
                modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')
                pi_user_obj = User.objects.get(username=pi_username)
                pi_user_obj.is_pi = True
                pi_user_obj.save()

                field_of_science_obj = FieldOfScience.objects.get(description=field_of_science)
                project_obj = Project.objects.create(
                    created=created,
                    modified=modified,
                    title=title.strip(),
                    pi=pi_user_obj,
                    description=description.strip(),
                    field_of_science=field_of_science_obj,
                    status=project_status_choices[project_status]
                )

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

                if not project_obj.projectuser_set.filter(user=pi_user_obj).exists():
                    project_user_obj = ProjectUser.objects.create(
                        user=pi_user_obj,
                        project=project_obj,
                        role=project_user_role_choices['PI'],
                        status=project_user_status_choices['ACT'],
                        enable_notifications=True
                    )
                elif project_obj.projectuser_set.filter(user=pi_user_obj).exists():
                    project_user_obj = ProjectUser.objects.get(project=project_obj, user=pi_user_obj)
                    project_user_obj.status=project_user_status_choices['ACT']
                    project_user_obj.save()

                    # print(project_obj)

        print('Finished adding projects')
