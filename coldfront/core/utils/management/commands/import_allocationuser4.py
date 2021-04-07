import datetime
import os
import json

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from csv import reader


from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.grant.models import (Grant, GrantFundingAgency,
                                         GrantStatusChoice)
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                           ProjectUser, ProjectUserRoleChoice,
                                           ProjectUserStatusChoice)
from coldfront.core.publication.models import Publication, PublicationSource
from coldfront.core.resource.models import (Resource, ResourceAttribute,
                                            ResourceAttributeType,
                                            ResourceType)
from coldfront.core.user.models import UserProfile


base_dir = settings.BASE_DIR

Users = ['Julia	Huang1',  # PI#1
         'Julia	Huang2',  # PI#2
         'Julia	Huang3',  
         'Matthew Holman2',
         'Paul Moorcroft',] # Director
          
resources = [
    # Storage
    ('Cluster', None, 'FAS Research Computing',
    'FAS Research Computing Storage Center', True, True, True),
    ('Cluster', None, 'Astronomy', 'Astronomy Cluster', True, False, False),
    ('Cluster', None, 'SEAS', 'SEAS Cluster', True, False, False),
    ('Cluster', None, 'Center for Astrophysics', 'Center for Astrophysics Cluster', True, False, False),

    # DRAFT -- Cluster Partitions scavengers -- DRAFT
    ('Cluster Partition', 'Chemistry', 'Chemistry-scavenger',
     'Scavenger partition on Chemistry cluster', True, False, False),
    ('Cluster Partition', 'Physics', 'Physics-scavenger',
     'Scavenger partition on Physics cluster', True, False, False),
    ('Cluster Partition', 'Industry', 'Industry-scavenger',
     'Scavenger partition on Industry cluster', True, False, False),


    # Cluster Partitions Users
    ('Cluster Partition', 'Chemistry', 'Astronomy-mholman',
     "Carl Gray's nodes", True, False, True),
    ('Cluster Partition', 'Physics', 'Biology-pmoorcroft',
     "Stephanie Foster's nodes", True, False, True),

    # Storage
    ('Storage', None, 'ProjectStorage',
    'level 0 storage', True, True, True),
    ('Storage', None, 'ProjectStorage',
    'level 1 storage', True, True, True),
    ('Storage', None, 'ProjectStorage',
    'level 2 storage', True, True, True),
    ('Storage', None, 'ProjectStorage',
    'level 3 storage', True, True, True),
    
    # Servers
    ('Server', None, 'server-mholman',
     "Server for Matthew Holman's research lab", True, False, True),
    ('Server', None, 'server-pmoorcroft',
    "Server for Paul Moorcroft's research lab", True, False, True),
]

class Command(BaseCommand):

    def handle(self, *args, **options):
        for user in Users:
            first_name, last_name = user.split()
            username = first_name[0].lower()+last_name.lower().strip()
            email = username + '@g.harvard.edu'
            User.objects.get_or_create(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                username=username.strip(),
                email=email.strip()
            )
        admin_user, _ = User.objects.get_or_create(username='superuser')
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()

        for resource in resources:
            resource_type, parent_resource, name, description, is_available, is_public, is_allocatable = resource
            resource_type_obj = ResourceType.objects.get(name=resource_type)
            if parent_resource != None:
                parent_resource_obj = Resource.objects.get(
                    name=parent_resource)
            else:
                parent_resource_obj = None

            Resource.objects.get_or_create(
                resource_type=resource_type_obj,
                parent_resource=parent_resource_obj,
                name=name,
                description=description,
                is_available=is_available,
                is_public=is_public,
                is_allocatable=is_allocatable
            )
        
        resource_obj = Resource.objects.get(name='server-mholman')
        resource_obj.allowed_users.add(User.objects.get(username='mholman'))
        resource_obj = Resource.objects.get(name='server-pmoorcroft')
        resource_obj.allowed_users.add(User.objects.get(username='pmoorcroft'))


        pi1 = User.objects.get(username='mholman2')
        pi1.userprofile.is_pi = True
        pi1.save()
        # create PI's project
        project_obj, _ = Project.objects.get_or_create(
            pi=pi1,
            title='Matthew Holman lab testing via backend',
            description='This is a testing description. As I am loading testing data via backend',
            field_of_science=FieldOfScience.objects.get(
                description='Other'),
            status=ProjectStatusChoice.objects.get(name='Active'),
            force_review=True
        )

        # This part is draft
        univ_hpc = Resource.objects.get(name='FAS Research Computing')
        for scavanger in ('Chemistry-scavenger', 'Physics-scavenger', 'Industry-scavenger', ):
            resource_obj = Resource.objects.get(name=scavanger)
            univ_hpc.linked_resources.add(resource_obj)
            univ_hpc.save()


        project_user_obj, _ = ProjectUser.objects.get_or_create(
            user=pi1,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active')
        )

        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now() + relativedelta(days=365)

        # Add PI cluster
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name='Active'),
            start_date=start_date,
            end_date=end_date,
            justification='I need x TB storage data.'
        )

        allocation_obj.resources.add(
            Resource.objects.get(name='Astronomy-mholman'))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name='Tier 0')
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value='mholman2')

        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi1,
            status=AllocationUserStatusChoice.objects.get(name='Active')
        )

        # Add university cluster
        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name='Active'),
            start_date=start_date,
            end_date=datetime.datetime.now() + relativedelta(days=10),
            justification='I need access to university cluster (mholman).'
        )

        allocation_obj.resources.add(
            Resource.objects.get(name='FAS Research Computing'))
        allocation_obj.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name='slurm_account_name')
        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value='mholman2')

        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj,
            user=pi1,
            status=AllocationUserStatusChoice.objects.get(name='Active'),
            usage = 666
        )




    #     print("Importing AllocationUser now...")
    #     allocationuser_obj = AllocationUser.objects.create(
    #                 username=username,
    #                 first_name=first_name,
    #                 last_name=last_name,
    #                 email=email,
    #                 is_active=is_active,
    #                 is_staff=is_staff,
    #                 is_superuser=is_superuser,
    #             )


    #     # open file in read mode
    #     for row in csv_reader:
    #         try:
    #             username = row[0]
    #             user = User.objects.get(username=username)
    #             #(username, "already exist, don't add to database")
    #             # if the user exists, I only need to append this existing user's group
    #             if not user.groups.filter(name = lab_name).exists():
    #                 my_group = Group.objects.get(name=lab_name)
    #                 my_group.user_set.add(user)
    #                 print ("user do not exist in", lab_name)
    #             continue
    #         # the type of row is 
    #         except ObjectDoesNotExist:
            
    #             username = row[0]
    #             full_name = row[1] 
    #             full_name_list = full_name.split()
    #             first_name = full_name_list[0]
            
                
    #             if (len(full_name_list) > 1):
    #                 last_name = full_name_list[1]
                
    #             else:
    #                 last_name = "N/A"
                    
                    
    #             email = row[2] 
    #             is_active = True
    #             is_staff = False
    #             is_superuser = False
    #             groups = lab_name 

    #             # creates my user object to load data from csv to GUI
    #             # create user object
    #             group_objs = []
    #             for group in groups.split(','):
    #                 group_obj, _ = Group.objects.get_or_create(name=group.strip()) # gets u the group object based on the group name
    #                 group_objs.append(group_obj)

                
    #             user_obj = User.objects.create(
    #                 username=username,
    #                 first_name=first_name,
    #                 last_name=last_name,
    #                 email=email,
    #                 is_active=is_active,
    #                 is_staff=is_staff,
    #                 is_superuser=is_superuser,
    #             )
    #             # add user to group
    #             if group_objs:
    #                 user_obj.groups.add(*group_objs) # add the group object to the user
    #             user_obj.save()
    # print('Finished adding users.')
