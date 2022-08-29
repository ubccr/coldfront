
import os
import csv
import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)
from coldfront.core.user.models import (UserProfile)
from coldfront.config.env import ENV

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        LOCALDATA_ROOT = ENV.str('LOCALDATA_ROOT', default=base_dir)
        file_path = os.path.join(LOCALDATA_ROOT, 'local_data/labs')
        pi_list_file= os.path.join(LOCALDATA_ROOT, 'local_data/pimap.csv')
        
        pi_dict = {}

        with open(pi_list_file, mode='r') as pimap:
            reader = csv.reader(pimap)
            pi_dict = {rows[0]:rows[1] for rows in reader}

        # Missing users csv
        userheader = ['GROUP', 'RC_USERNAME','ROLE']
        missing_users = open('local_data/missing_users.csv', 'w')
        writer = csv.writer(missing_users)
        writer.writerow(userheader)
 
        lab_list = os.listdir(file_path)
        for lab in lab_list:
            lab_temp = lab.split(".")
            lab_name = lab_temp[0].split("-")
            pi_username= pi_dict.get(lab_name[1])
            title = lab_name[1].strip()
            description = "Allocations for " + title

            print("Loading Project data for : " + title)
                      
            
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
            
            created = datetime.datetime.now(tz=timezone.utc) 
            modified = datetime.datetime.now(tz=timezone.utc) 

            user_dict = []
            csv_file =file_path+'/'+lab 
            with open(csv_file, 'r') as read_obj:
                reader = csv.DictReader(read_obj)
                for row in reader:
                    user_dict.append(row) 
            try:
                filtered_query = Project.objects.filter(title = title)
                if not filtered_query.exists():
                    print("Creating new project:" + title)
                    for row in user_dict: 
                        user = row['samaccountname']
                        if (user == pi_username):
                            field_of_science=row['department']
                            try:
                                pi_user_obj = get_user_model().objects.get(username=user)
                                pi_user_obj.is_pi = True
                                pi_user_obj.save()
                                project_status = "New"
                                try: 
                                    field_of_science_obj = FieldOfScience.objects.get(description=field_of_science)
                                except:
                                    print(field_of_science)
                                    field_of_science_obj = FieldOfScience(
                                    is_selectable='True',
                                    description=field_of_science,
                                    )
                                    field_of_science_obj.save()
                    
                                project_obj = Project.objects.create(
                                    created=created,
                                    modified=modified,
                                    title=title,
                                    pi=pi_user_obj,
                                    description=description.strip(),
                                    field_of_science=field_of_science_obj,
                                    status=project_status_choices[project_status]
                                )           
                            print("Project %s created with PI %s", title, pi_username)
                            except get_user_model().DoesNotExist:
                                print("PI User missing: ", user)
                                tocsv = [title, user,'PI']
                                writer.writerow(tocsv) 
                                continue
                project_obj = Project.objects.get(title = title)
                if (project_obj != ""):
                    for project_user in user_dict:
                        if (project_user != ""):
                            username = project_user['samaccountname']
                            enable_email = False
                            if (username == pi_username):
                                role = 'PI'
                                enable_email = True
                            else:
                                role = 'U'
                            project_user_status = 'ACT'
                            try:
                                user_obj = get_user_model().objects.get(username=username)
                            except get_user_model().DoesNotExist:
                                print("couldn't add user", username)
                                tocsv = [title, username,'User']
                                writer.writerow(tocsv) 
                                continue
                            if not project_obj.projectuser_set.filter(user=user_obj).exists():
                                project_user_obj = ProjectUser.objects.create(
                                user=user_obj,
                                project=project_obj,
                                role=project_user_role_choices[role],
                                status=project_user_status_choices[project_user_status],
                                enable_notifications=enable_email
                                )
                            elif project_obj.projectuser_set.filter(user=user_obj).exists():
                                project_user_obj = ProjectUser.objects.get(project=project_obj, user=user_obj)
                                project_user_obj.status=project_user_status_choices['ACT']
                                project_user_obj.save() 
            except Exception as e:
                print(f'Error {e}')
        missing_users.close()
