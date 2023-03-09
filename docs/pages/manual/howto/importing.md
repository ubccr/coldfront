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
```

Line 29 here is especially important as it contains different information about the users. The CSV file that you import may have a different order then this, if so, it is important that line 29 reflects that order.

```username, first_name, last_name, email, is_active, is_staff, is_superuser = m```

can be changed to include

```username, last_name, first_name email, is_active, is_staff, is_superuser = m```

It is important that the username is to be unique. The same username cannot be shared by multiple people.

Place this code in ```coldfront\core\utils\management\commands``` along with your new csv file. It is important that your csv file is in the same directory as this code

#### Sample Data

```
username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups
joe11, joe,smith,joesmith@.com,True,False,True,True
astridschmidt, Astrid,Schmidt,astridschmidt@astrid.edu,True,False,True,True
HarshithGupta,Harshith,Gupta,harshith_oob@gemsedu.com,False,False,False,True
```




### Importing Project Data
Place this code in ```coldfront\core\utils\management\commands``` along with your new csv file, making sure that they are in the same directory.

**NOTE:** The "created" and "modified" fields are both dates, and must be in a specific format.
YYYY-MM-DD HH:MM:SS.MS
(2023-01-11 01:11:10). 

Create a csv file 

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

#### Sample Data
```
created, modified, title, pi_username, description, field_of_science, project_status, user_info
2023-01-11 01:11:10,2022-10-10 7:07:09,fakeproject,astridschmidt,Atomics,Physics,Active,lucas11:U:True:ACT
2023-01-10 01:11:12,2022-10-10 7:08:06,fakeproject2,joe11,Statistical Analysis,Physics,Active,lucas11:U:True:ACT
2023-01-09 01:11:01,2022-10-10 7:09:07,fakeproject3,karthik22,Informatics,Physics,Active,lucas11:U:True:ACT
2023-01-08 01:11:02,2022-10-10 7:10:08,fakeproject4,henry_wilderman,Artificial Intelligence,Physics,Active,lucas11:U:True:ACT
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

base_dir = settings.BASE_DIR


def get_role_and_pi_mapping():
    delimiter = '$'
    file_path = os.path.join(base_dir, 'local_data', 'grants_role_pi.tsv')

    mapping = {}
    with open(file_path, 'r') as fp:
        for line in fp:
            if line.startswith('#'):
                continue

            PROJECT_TITLE, GRANT_TITLE, RF_Award_Number, ROLE, PI = line.strip().split(delimiter)

            if ROLE == 'coPI':
                ROLE = 'CoPI'

            unique_key = PROJECT_TITLE + GRANT_TITLE
            mapping[unique_key] = {
                'role': ROLE,
                'pi': PI,
                'rf_award_number': RF_Award_Number
            }
    return mapping


class Command(BaseCommand):

    def grant():
        print('Adding grants ...')
        Grant.objects.all().delete()

        delimiter = '\t'
        file_path = os.path.join(base_dir, 'local_data', 'grants.tsv')

        agency_mapping = {
            'AHA': 'Other',
            'Army Research Laboratory, MURI': 'Other',
            'Canadian Institutes of Health Research (CIHR)': 'Other',
            'Department of Energy': 'Department of Energy (DOE)',
            'Department of Homeland Security': 'Other',
            'DOE': 'Department of Energy (DOE)',
            'Federal Rail Administration (FRA)': 'Other',
            'Google Inc': 'Other',
            'Hologic Inc.': 'Other',
            'Internal - UB OVPRED (Grant Resubmission Award)': 'Other',
            'NASA': 'National Aeronautics and Space Administration (NASA)',
            'National Institute on Drug Abuse (NIDA)': 'National Institutes of Health (NIH)',
            'National Institutes of Health': 'National Institutes of Health (NIH)',
            'National Nuclear Security Administration': 'Other',
            'National Science Foundation': 'National Science Foundation (NSF)',
            'Navy STTR': 'Other',
            'New York State Center of Excellence in Materials Informatics': 'Other',
            'New York State NYSTAR': "Empire State Development's Division of Science, Technology and Innovation (NYSTAR)",
            'NHLBI': 'National Institutes of Health (NIH)',
            'NIH': 'National Institutes of Health (NIH)',
            'NIH / NLM': 'National Institutes of Health (NIH)',
            'NIH NCATS': 'National Institutes of Health (NIH)',
            'NIH-NHLBI': 'National Institutes of Health (NIH)',
            'NIH/NHLBI': 'National Institutes of Health (NIH)',
            'NOAA': 'Other',
            'Nomura Foundation': 'Other',
            'NSF': 'National Science Foundation (NSF)',
            'nsf': 'National Science Foundation (NSF)',
            'NSF CBET Energy for Sustainability Program': 'National Science Foundation (NSF)',
            'NSF:CIF': 'National Science Foundation (NSF)',
            'NVIDIA': 'Other',
            'NY State Department of Health': 'New York State Department of Health (DOH)',
            'NYS Department of Economic Development': 'New York State (NYS)',
            'NYSTAR through RPI': 'Other',
            'NYSTEM': 'Other',
            'Office of Naval Research': 'Other',
            'RENEW (UB)': 'Other',
            'RENEW Institute - University at Buffalo': 'Other',
            'SUNY': 'Other',
            'UB RENEW': 'Other',
            'UB STEM Mentored Undergraduate Research Initiative': 'Other',
            'UBCAT': 'Other',
            'University at Buffalo CAS and OVPRED': 'Other',
            'US Army Research Office': 'Other',
            'US Department of Energy/NETL': 'Other',
            'VA': 'Other',
            'Wisconsin Highway Research Program': 'Other',
            'Funded by UB through funds for the Samuel P. Capen Professor': 'Other',
            'Arthritis Foundation': 'Other',
            'HRI-Roswell Park': 'Other',
            'DARPA': 'Other',
            'City of Buffalo / Buffalo Sewer Authority': 'Other',
            'NYS Empire State Development': 'Empire State Development (ESD)',
            'NIAMS': 'National Institutes of Health (NIH)',
        }

        role_pi_mapping = get_role_and_pi_mapping()

        with open('sample_csv_for_grants') as fp:
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

        #doesnt work
        print('Finished adding grants.')
    grant()
```

#### Sample Data

```
created, modified, project__title, project__pi__username, project_status, project_number, title, funding_agency, project_start, project_end, percent_credit, direct_funding, total_amount_awarded, status
2023-01-11 01:11:10,2022-10-10 7:07:09,fakeproject, lucas11,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active
2023-01-10 01:11:10,2022-10-09 7:07:09,fakeproject, astridschmidt,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active
2023-01-12 01:11:10,2022-10-08 7:07:09,fakeproject, joe11,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active
2023-01-09 01:11:10,2022-10-07 7:07:09,fakeproject, HarshithGupta,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active
2023-01-08 01:11:10,2022-10-12 7:07:09,fakeproject, lucas11,Active,7168891383, NSF, NASA,2023-01-11 01:11:10,2023-11-11 01:11:10,30,200000,1200000,Active

```

### Importing Publications

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
from coldfront.core.publication.models import Publication, PublicationSource

class Command(BaseCommand):

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
                    print('Violate unique constraint')
                    print(created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi)


        print('Publications Added!')
    import_publications('sample_csv_for_publications.csv')
```

#### Sample Data
```
created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi
01/11/2023,10/10/2022,fakeproject,Active,astridschmidt,project1,Astrid Schmidt,Science,2022,10.0000/000000000
```

### Importing Rescources

```
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


class Command(BaseCommand):

    def import_data_rescourece(filename):
        print('Adding resources ...')
        AttributeType.objects.all().delete()
        ResourceType.objects.all().delete()
        ResourceAttributeType.objects.all().delete()
        ResourceType.objects.all().delete()
        Resource.objects.all().delete()
        ResourceAttribute.objects.all().delete()
        # with open(os.path.join(base_dir, 'local_data/R1_attribute_types.tsv')) as file:
        #     for name in file:
        #         attribute_type_obj, created = AttributeType.objects.get_or_create(
        #             name=name.strip())
        #         # print(attribute_type_obj, created)

        # with open(os.path.join(base_dir, 'local_data/R2_resource_types.tsv')) as file:
        #     for line in file:
        #         name, description = line.strip().split('\t')
        #         resource_type_obj, created = ResourceType.objects.get_or_create(
        #             name=name.strip(), description=description.strip())
        #         # print(resource_type_obj, created)

        # with open(os.path.join(base_dir, 'local_data/R3_resource_attributes_types.tsv')) as file:
        #     next(file)
        #     f=csv.reader(file)
        #     for line in file:
        #         attribute_type_name, resource_type_name, name, required = line
        #         resource_attribute_type_obj, created = ResourceAttributeType.objects.get_or_create(
        #             attribute_type=AttributeType.objects.get(
        #                 name=attribute_type_name),
        #             name=name,
        #             is_required=bool(required))
        #         # print(resource_attribute_type_obj, created)

        # with open(os.path.join(base_dir, 'local_data/R4_resources.tsv')) as file:
        #     for line in file:
        #         # print(line)
        #         resource_type_name, name, description, parent_name = line.strip().split('\t')
        #         resource_obj, created = Resource.objects.get_or_create(
        #             resource_type=ResourceType.objects.get(name=resource_type_name),
        #             name=name,
        #             description=description.strip())

        #         if parent_name != 'None':
        #             parent_resource_obj = Resource.objects.get(name=parent_name)
        #             resource_obj.parent_resource = parent_resource_obj
        #             resource_obj.save()

                # print(resource_obj, created)
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
            #todo
    import_data_rescourece('sample_csv_for_rescources.csv')
```




#### Sample Data

```
resource_type_name, resource_attribute_type_name, resource_attribute_type_type_name, resource_name, value
Cluster,slurm_specs,Project ID,University Cloud Storage,230
Unknown,slurm_specs,Project ID,University Cloud Storage,130
Unknown2,slurm_specs,Project ID,University Cloud Storage,330

```




