import datetime
import os
import json

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from csv import reader

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)
from coldfront.core.user.models import (UserProfile)

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding projects ...')
        delimiter = ','

        lab_pi_name_list = ['zhuang_lab,xzhuang']
        lab_pi_list = lab_pi_name.split(",")
        pi_name = lab_pi_list[1]
        lab_name = lab_pi_list[0]


        file_name = lab_name + '.csv'
        file_path = os.path.join(base_dir, 'local_data', file_name)

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

        user_info = ""
        with open (file_path, 'r') as read_obj:
            csv_reader = reader(read_obj) # opt out the first line
            first_line = read_obj.readline()  # skip firstline
            pi_potential_name = ""
            for row in csv_reader:
                user = row[0]
                if (row[3] == 'FACULTY'):
                    pi_potential_name = row[3]
                    user_info = user_info + user + ',PI' + ',PI' + ',ACT;'

                else:
                    user_info = user_info + user + ',U' + ',U' + ',ACT;'


        with open (file_path, 'r') as read_obj:
            csv_reader = reader(read_obj) # opt out the first line
            first_line = read_obj.readline()

            created = "2021-02-01 10:00:00" # feeding dummy data for now
            modified = "2021-03-01 10:00:00" # feeding dummy data for now
            title = lab_name
            pi_username = lab_name.split("_")
            pi_username = pi_username[0] # put in username
            pi_username = pi_potential_name
            pi_username = pi_name
            description = "could I have 1 TB of data, please?"
            field_of_science = "Other"
            project_status = "New"


            created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
            modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')
            # find pi object in the file
            pi_user_obj = get_user_model().objects.get(username=pi_username)

            pi_user_obj.is_pi = True
            pi_user_obj.save()
            # find the project
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
                if (project_user != ""): # if excel file read in line is not empty
                    username, role, enable_email, project_user_status = project_user.split(',')
                    if enable_email == 'True':
                        enable_email = True
                    else:
                        enable_email = False
                    print(username, role, enable_email, project_user_status)
                    try:
                        user_obj = get_user_model().objects.get(username=username)

                    except ObjectDoesNotExist:
                        print("couldn't add user", username)
                        continue

                    project_user_obj = ProjectUser.objects.create(
                        user=user_obj,
                        project=project_obj,
                        role=project_user_role_choices[role],
                        status=project_user_status_choices[project_user_status],
                        enable_notifications=enable_email
                    )
            # when import a project, we can import the user to project as well
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



        print('Finished adding projects')
