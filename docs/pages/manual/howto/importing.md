# Importing data into ColdFront

This is a guide on importing data into ColdFront from a preexisting system.

## Gathering Data

The first step before importing data into ColdFront is gathering it. ColdFront allows users to maintain records of Users, Projects, Grants etc; so a user can choose to import data for all of these records. Here, we will take an example of Users. Create a spreadsheet with a  header file that includes all of the information about a user that you wish to import into ColdFront, and save it as a .csv file. This can be done using Microsoft Excel or Google Sheets.

**NOTE:** CSV (or Comma Separated Values) files are split by commas. Make sure that there are no fields of data have commas in them
//But this can be changed

### Importing User Data

The following sample code allows for importing a csv file of Users into ColdFront's databases.

```
import os
import csv

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

def import_model(filename):
    with open(filename) as file:
        f=csv.reader(file)
        for m in f:
            print(m)
            username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups = m.strip().split(',')
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
            print(user_obj)
            user_obj.save()
```

Line 29 here is especially important as it contains different information about the users. You can add to this if you wish, by simply adding new parameters to the left hand side of the code. For example

```username, first_name, last_name, email, is_active, is_staff, is_superuser = m.strip().split(',')```

can be changed to include

```username, first_name, last_name, email, address, date_of_birth,is_active, is_staff, is_superuser = username, first_name, last_name, email, is_active, is_staff, is_superuser```

Make sure to update this in ```user_obj``` in line 30. 

Place this code in ```coldfront\core\utils\management\commands```

### Importing Project Data

```
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
```

### Importing Grants
```
import datetime
import os
import pprint
import csv

import pytz
from django.conf import settings
from django.core.management.base import BaseCommand

from coldfront.core.grant.models import (Grant, GrantFundingAgency,
                                          GrantStatusChoice)
from coldfront.core.project.models import Project
def import_grant(filename):
    with open(filename, 'r') as fp:
        f=csv.reader(fp)
        for line in f:
            if line.startswith('#'):
                continue
            created, modified, project__title, project__pi__username, project_status, project_number, title, funding_agency, project_start, project_end, percent_credit, direct_funding, total_amount_awarded, status = line.strip().split(",")

            created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
            modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')
            project_start = datetime.datetime.strptime(project_start, '%Y-%m-%d')
            project_end = datetime.datetime.strptime(project_end, '%Y-%m-%d')

            if funding_agency in agency_mapping:
                funding_agency_obj = GrantFundingAgency.objects.get(name=agency_mapping[funding_agency])
                if agency_mapping[funding_agency] == 'Other':
                    other_funding_agency = funding_agency
                else:
                    other_funding_agency = ''
            else:
                funding_agency_obj = GrantFundingAgency.objects.get(name='Other')
                other_funding_agency = funding_agency

            unique_key = project__title + title
            if unique_key in role_pi_mapping:
                role = role_pi_mapping[unique_key].get('role')
                grant_pi_full_name = role_pi_mapping[unique_key].get('pi')
                rf_award_number = role_pi_mapping[unique_key].get('rf_award_number')
            else:
                role = 'PI'
                grant_pi_full_name = ''
                rf_award_number = 0

            try:
                project_obj = Project.objects.get(title=project__title.strip(),
                pi__username=project__pi__username.strip(), status__name=project_status)
            except:
                print(project__title, project__pi__username)


            grant_status_choice_obj = GrantStatusChoice.objects.get(name=status.title())
            grant_obj, created = Grant.objects.get_or_create(
                created=created,
                modified=modified,
                project=project_obj,
                grant_number=project_number,
                title=title,
                role=role,
                grant_pi_full_name=grant_pi_full_name,
                funding_agency=funding_agency_obj,
                other_funding_agency=other_funding_agency,
                other_award_number=rf_award_number,
                grant_start=project_start,
                grant_end=project_end,
                percent_credit=percent_credit,
                direct_funding=direct_funding,
                total_amount_awarded=total_amount_awarded,
                status=grant_status_choice_obj
                )
```

