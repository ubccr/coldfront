# Importing data into ColdFront

This is a guide on importing data into ColdFront from a preexisting system.

## Gathering Data

The first step before importing data into ColdFront is gathering it. ColdFront allows users to maintain records of Users, Projects, Grants etc; so a user can choose to import data for all of these records. Here, we will take an example of Users. Create a spreadsheet with a  header file that includes all of the information about a user that you wish to import into ColdFront, and save it as a .csv file. This can be done using Microsoft Excel or Google Sheets.

**NOTE:** CSV (or Comma Separated Values) files are split by commas. Make sure that there are no fields of data have commas in them

### Importing User Data

The following sample code allows for importing a csv file of Users into ColdFront's databases. Create a file called users_import.py using

```vim users_import.py```

and paste the following code/

```py linenums="1"
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
            if group_objs:
                    user_obj.groups.add(*group_objs)
                if 'pi' in groups.split(','):
                    user_obj.is_pi = True
    import_model("user_data.csv")
```

Line 29 here is especially important as it contains different information about the users. The CSV file that you import may have a different order then this, if so, it is important that line 29 reflects that order.

```username, first_name, last_name, email, is_active, is_staff, is_superuser = m```

can be changed to include

```username, last_name, first_name email, is_active, is_staff, is_superuser = m```

It is important that the username is to be unique. The same username cannot be shared by multiple people.

Load your csv file in the same directory as the aformentioned ```users_import.py``` and run the following command

```coldfront shell < users_import.py```


#### Sample Data

```
username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups
joe11, joe, smith,joesmith@example.com, True, False, True, True, Academic
astridschmidt, Astrid, Schmidt, astridschmidt@example.com, True, False, True, True
HarshithGupta, Harshith, Gupta, harshith@example.com, False, False, False, True
```




### Importing Project Data
Place this code in ```coldfront\core\utils\management\commands``` along with your new csv file, making sure that they are in the same directory.

**NOTE:** The "created" and "modified" fields are both dates, and must be in a specific format.
YYYY-MM-DD HH:MM:SS.MS
(2023-01-11 01:11:10). 

Create a csv file 

```python linenums="1"
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
    project_status_choices = {}
    project_status_choices['Active'] = ProjectStatusChoice.objects.get(name='Active')

    project_user_role_choices = {}
    project_user_role_choices['PI'] = ProjectUserRoleChoice.objects.get(name='Manager')
    
    project_user_status_choices = {}
    project_user_status_choices['ACT'] = ProjectUserStatusChoice.objects.get(name='Active')
    
    ProjectUserStatusChoice.objects.get_or_create(name=choice)

    with open(filename) as file:
        next(file)
        f=csv.reader(file, delimiter=',')
        for m in f:
            created, modified, title, pi_username, description, field_of_science, project_status, user_info = m
            created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
            modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')
            pi_user_obj = User.objects.get(username=pi_username)
            pi_user_obj.is_pi = True
            pi_user_obj.save()

        for project_user in user_info.split(';'):
            print("user info",user_info)
            print("project_user",project_user)
            username, role, enable_email, project_user_status = project_user.split(':')
            if enable_email == 'True':
                enable_email = True
            else:
                enable_email = False
            # print(username, role, enable_email, project_user_status)
            user_obj = User.objects.get(username=username)

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
            print("the save has done!")
                    
import_model_projects('project_data.csv')
```

#### Sample Data
```
created, modified, title, pi_username, description, field_of_science, project_status, user_info
2023-01-11 01:11:10,2022-10-10 7:07:09,fakeproject,astridschmidt,Atomics,Physics,Active,lucas11:U:True:ACT
2023-01-10 01:11:12,2022-10-10 7:08:06,fakeproject2,joe11,Statistical Analysis,Physics,Active,lucas11:U:True:ACT
2023-01-09 01:11:01,2022-10-10 7:09:07,fakeproject3,karthik22,Informatics,Physics,Active,lucas11:U:True:ACT
2023-01-08 01:11:02,2022-10-10 7:10:08,fakeproject4,henry_wilderman,Artificial Intelligence,Physics,Active,lucas11:U:True:ACT
```




### Importing Grants
```python linenums="1"
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

base_dir = settings.BASE_DIR



def import_grants(filename):
    print('Adding grants ...')
    agency_mapping = {
        'NSF': 'National Science Foundation (NSF)',
        'nsf': 'National Science Foundation (NSF)',
    }

    role_pi_mapping = get_role_and_pi_mapping()

    with open(filename) as fp:
        next(fp)
        f=csv.reader(fp)
        for line in fp:
            created, modified, project__title, project__pi__username, project_status, project_number, title, funding_agency, project_start, project_end, percent_credit, direct_funding, total_amount_awarded, status = line
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

    print('Finished adding grants.')
import_grants('grants_data.csv')
```

#### Sample Data

```
created, modified, project__title, project__pi__username, project_status, project_number, title, funding_agency, project_start, project_end, percent_credit, direct_funding, total_amount_awarded, status
2023-01-11 01:11:10,2022-10-10 7:07:09,fakeproject, lucas11,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active
2023-01-10 01:11:10,2022-10-09 7:07:09,fakeproject, astridschmidt,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active


```

### Importing Publications

```python linenums="1"
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
from coldfront.core.publication.models import Publication, PublicationSource


def import_publications(filename):
    print('Adding publications ...')
    doi_source = PublicationSource.objects.get(name='doi')

    with open(filename) as file:
        next(file)
        f=csv.reader(file)
        for line in f:
    
            created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi = line

            created = datetime.datetime.strptime(created.split('.')[0], '%m/%d/%Y')
            modified = datetime.datetime.strptime(modified.split('.')[0], '%m/%d/%Y').strftime('%Y-%m-%d')
            project_obj = Project.objects.get(pi__username=pi_username, title=project_title, status__name=project_status)

            try:
                Publication.objects.get_or_create(
                    created=created,
                    modified=modified,
                    project=project_obj,
                    title=publication_title.encode("ascii", errors="ignore").decode(),
                    author=author.encode("ascii", errors="ignore").decode(),
                    journal=author.encode("ascii", errors="ignore").decode(),
                    year=publication_year,
                    unique_id=doi,
                    source=doi_source
                )
            except Exception as e:
                print(e)
                print('Violated unique constraint')
                print(created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi)


    print('Publications Added!')
import_publications('publications_data.csv')
```

#### Sample Data
```
created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi
01/11/2023,10/10/2022,fakeproject,Active,astridschmidt,project1,Astrid Schmidt,Science,2022,10.0000/000000000
```

### Importing Rescources

```python linenums="1"
import os
import csv

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (AttributeType, Resource,
                                              ResourceAttribute,
                                              ResourceAttributeType,
                                              ResourceType)

base_dir = settings.BASE_DIR


def import_resource(filename):
    print('Adding resources ...')

    with open(filename) as file:
        next(file)
        f=csv.reader(file)
        for line in f:
            resource_type_name, resource_attribute_type_name, resource_attribute_type_type_name, resource_name, value = line

            if resource_attribute_type_name == 'slurm_specs':
                value = 'QOS+=' + value + ':Fairshare=100'


            if resource_attribute_type_name == 'Access':
                if value == 'Public':
                    is_public = True
                else:
                    is_public = False
                resource_obj = Resource.objects.get(name=resource_name)
                resource_obj.is_public = is_public
                resource_obj.save()

            elif resource_attribute_type_name == 'Status':
                if value == 'Active':
                    is_available = True
                else:
                    is_available = False
                resource_obj = Resource.objects.get(name=resource_name)
                resource_obj.is_available = is_available
                resource_obj.save()

            elif resource_attribute_type_name == 'AllowedGroups':
                resource_obj = Resource.objects.get(name=resource_name)
                for group in value.split(','):
                    group_obj, _ = Group.objects.get_or_create(name=group.strip())

                    resource_obj.allowed_groups.add(group_obj)
                resource_obj.save()

            else:
                resource_attribute_obj, created = ResourceAttribute.objects.get_or_create(
                    resource_attribute_type=ResourceAttributeType.objects.get(name=resource_attribute_type_name, attribute_type__name=resource_attribute_type_type_name),
                    resource=Resource.objects.get(name=resource_name),
                    value=value.strip())


    resource_obj = Resource.objects.get(name='UB-HPC')
    for children_resource in ['Industry-scavenger', 'Chemistry-scavenger', 'Physics-scavenger', 'MAE-scavenger']:
        children_resource_obj = Resource.objects.get(name=children_resource)
        resource_obj.linked_resources.add(children_resource_obj)



    for unsubscribable in ['Industry-scavenger', 'Chemistry-scavenger', 'Physics-scavenger', 'MAE-scavenger', 'Physics', 'Chemistry', 'MAE']:
        resource_obj = Resource.objects.get(name=unsubscribable)
        resource_obj.is_allocatable = False
        resource_obj.save()
import_resource('resources_data.csv')
```




#### Sample Data

```
resource_type_name, resource_attribute_type_name, resource_attribute_type_type_name, resource_name, value
Cluster,slurm_specs,Project ID,University Cloud Storage,230


```
## Commands

In the case that your data fits the parameters exactly, you can use the predefined commands to import your data into Coldfront

The general command syntax is 
``` coldfront import_new_x -i filepath```

Users-

``` coldfront import_new_users -i filepath```

Publications-

``` coldfront import_new_publications -i filepath```

Resources-

``` coldfront import_new_resources -i filepath```

Grants-

``` coldfront import_new_grants -i filepath```

Projects-

``` coldfront import_new_projects -i filepath```






