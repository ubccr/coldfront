import csv
import datetime
import time

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from coldfront.core.user.models import UserProfile
from coldfront.core.project.models import (Project,
                                           ProjectTypeChoice,
                                           ProjectStatusChoice,
                                           ProjectUser,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice)
from coldfront.core.allocation.models import (Allocation,
                                              AllocationStatusChoice,
                                              AllocationAttributeType,
                                              AllocationAttribute,
                                              AllocationUser,
                                              AllocationUserStatusChoice,
                                              AllocationUserRoleChoice)
from coldfront.core.resource.models import Resource
from coldfront.plugins.slate_project.utils import LDAPModify


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=str)
        parser.add_argument("--limit", type=int)

    def generate_slurm_account_name(self, project_obj):
        num = str(project_obj.pk)
        string = '00000'
        string = string[:-len(num)] + num
        project_type = project_obj.type.name
        letter = 'r'
        if project_type == 'Class':
            letter = 'c'

        return letter + string
    
    def get_info(self, info, line, current_project):
        if f'"{info}"' in line:
            split_line = line.split(':', 1)
            line_info = split_line[1].strip()
            if not info == 'id':
                if not line_info == 'null':
                    line_info = line_info[1:-1]
            try:
                line_info = int(line_info)
            except ValueError:
                pass

            current_project[info] = line_info

    def get_new_end_date_from_list(self, expire_dates, check_date=None, buffer_days=0):
        """
        Finds a new end date based on the given list of expire dates.

        :param expire_dates: List of expire dates
        :param check_date: Date that is checked against the list of expire dates. If None then it's
        set to today
        :param buffer_days: Number of days before the current expire date where the end date should be
        set to the next expire date
        :return: A new end date
        """
        if check_date is None:
            check_date = datetime.date.today()

        expire_dates.sort()

        buffer_dates = [date - datetime.timedelta(days=buffer_days) for date in expire_dates]

        end_date = None
        total_dates = len(expire_dates)
        for i in range(total_dates):
            if check_date < expire_dates[i]:
                if check_date >= buffer_dates[i]:
                    end_date = expire_dates[(i + 1) % total_dates]
                    if (i + 1) % total_dates == 0:
                        end_date = end_date.replace(end_date.year + 1)
                else:
                    end_date = expire_dates[i]
                break
            elif i == total_dates - 1:
                expire_date = expire_dates[0]
                end_date = expire_date.replace(expire_date.year + 1)

        return end_date
    
    def create_allocation_attribute(self, allocation_obj, aa_type, value):
        if value and value != 'null':
            if value == 'true':
                value = 'Yes'
            elif value == 'false':
                value = 'No'

            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name=aa_type, linked_resources__name__exact="Slate Project"),
                allocation=allocation_obj,
                value=value
            )

    def handle(self, *args, **kwargs):
        if not kwargs.get("csv"):
            raise CommandError("CSV does not exist")
        
        slate_project_import_limit = kwargs.get("limit")
        if slate_project_import_limit is not None and slate_project_import_limit <= 0:
            raise CommandError("The limit must be > 0")

        print('Importing Slate Projects...')
        ldap_conn = LDAPModify()
        start_time = time.time()
        file_name = kwargs.get("csv")
        slate_projects = []
        with open(file_name, 'r') as ssa_dump:
            csv_reader = csv.reader(ssa_dump)
            next(csv_reader)
            for line in csv_reader:
                slate_project = {
                    "abstract": line[0],
                    "account": line[1],
                    "advisor": line[2],
                    "allocated_quantity": line[3],
                    "billable_quantity": line[4],
                    "campus_affiliation": line[5],
                    "created_at": line[6],
                    "deactivate_after": line[7],
                    "deactivated_at": line[8],
                    "default_ncto_quantity": line[9],
                    "discretionary_ncto_quantity": line[10],
                    "fiscal_officer": line[11],
                    "id": line[12],
                    "is_active": line[13],
                    "is_ephi_intended": line[14],
                    "namespace_class": line[15],
                    "namespace_entry": line[16],
                    "owner_email": line[17],
                    "owner_firstname": line[18],
                    "owner_lastname": line[19],
                    "owner_netid": line[20],
                    "parent_subscription_id": line[21],
                    "percent": line[22],
                    "project_title": line[23],
                    "project_url": line[24],
                    "service_type_id": line[25],
                    "start_date": line[26],
                    "sub_account": line[27],
                    "subscription_chain_guid": line[28],
                    "ticket_id": line[29],
                    "updated_at": line[30],
                    "title": line[31],
                    "can_be_pi": line[32],
                    # "read_write_users": line[33],
                    # "read_only_users": line[34]
                }
                slate_projects.append(slate_project)

        # Non faculty, staff, and ACNP should be put in their own projects with a HPFS member as the PI.
        hpfs_pi =  User.objects.get(username="thcrowe")
        project_end_date = self.get_new_end_date_from_list(
            [datetime.datetime(datetime.datetime.today().year, 6, 30), ],
            datetime.datetime.today(),
            90
        )
        if slate_project_import_limit is not None:
            slate_projects = slate_projects[:slate_project_import_limit]
        for slate_project in slate_projects:
            user_obj, _ = User.objects.get_or_create(username=slate_project.get('owner_netid'))
            project_user_role = ProjectUserRoleChoice.objects.get(name='Manager')
            if slate_project.get('can_be_pi') == 'True':
                project_obj, _ = Project.objects.get_or_create(
                    title=slate_project.get('project_title'),
                    description=slate_project.get('abstract'),
                    pi=user_obj,
                    max_managers=3,
                    requestor=user_obj,
                    type=ProjectTypeChoice.objects.get(name='Research'),
                    status=ProjectStatusChoice.objects.get(name='Active'),
                    end_date=project_end_date
                )

                project_obj.slurm_account_name = self.generate_slurm_account_name(project_obj)
                project_obj.save()
            else:
                project_obj, _ = Project.objects.get_or_create(
                    title=slate_project.get('project_title'),
                    description=slate_project.get('abstract'),
                    pi=hpfs_pi,
                    max_managers=3,
                    requestor=user_obj,
                    type=ProjectTypeChoice.objects.get(name='Research'),
                    status=ProjectStatusChoice.objects.get(name='Active'),
                    end_date=project_end_date
                )

                project_obj.slurm_account_name = self.generate_slurm_account_name(project_obj)
                project_obj.save()

                ProjectUser.objects.get_or_create(
                    user=hpfs_pi,
                    project=project_obj,
                    role=project_user_role,
                    status=ProjectUserStatusChoice.objects.get(name='Active')
                )

            read_write_users = ldap_conn.get_users(slate_project.get('namespace_entry'))
            read_only_users = ldap_conn.get_users(slate_project.get('namespace_entry') + '-ro')
            all_users = read_write_users + read_only_users
            for user in all_users:
                enable_notifications = True
                if not user:
                    continue
                user_obj, _ = User.objects.get_or_create(username=user)
                user_profile_obj = UserProfile.objects.get(user=user_obj)
                project_user_role = ProjectUserRoleChoice.objects.get(name='User')
                if user_profile_obj.title == 'group':
                    project_user_role = ProjectUserRoleChoice.objects.get(name='Group')
                    enable_notifications = False

                if user_obj == project_obj.pi:
                    project_user_role = ProjectUserRoleChoice.objects.get(name='Manager')

                ProjectUser.objects.get_or_create(
                    user=user_obj,
                    project=project_obj,
                    role=project_user_role,
                    enable_notifications=enable_notifications,
                    status=ProjectUserStatusChoice.objects.get(name='Active')
                )

            allocation_start_date = slate_project.get('start_date').split('/')
            allocation_start_date = '-'.join(
                [allocation_start_date[2], allocation_start_date[0], allocation_start_date[1]]
            )

            allocation_obj, created = Allocation.objects.get_or_create(
                project=project_obj,
                status=AllocationStatusChoice.objects.get(name='Active'),
                start_date=allocation_start_date,
                end_date=project_end_date,
                is_changeable=True
            )
            if created:
                allocation_obj.resources.add(Resource.objects.get(name='Slate Project'))

            if not all_users:
                user_obj, created = User.objects.get_or_create(username=slate_project.get('owner_netid'))
                allocation_user_obj, created = AllocationUser.objects.get_or_create(
                    user=user_obj,
                    allocation=allocation_obj,
                    status=AllocationUserStatusChoice.objects.get(name='Active')
                )
                if created:
                    allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                    allocation_user_obj.save()
            else:
                for user in read_write_users:
                    if not user:
                        continue
                    user_obj, created = User.objects.get_or_create(username=user)
                    allocation_user_obj, created = AllocationUser.objects.get_or_create(
                        user=user_obj,
                        allocation=allocation_obj,
                        status=AllocationUserStatusChoice.objects.get(name='Active')
                    )

                    if created:
                        allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                        allocation_user_obj.save()

                for user in read_only_users:
                    if not user:
                        continue
                    user_obj, created = User.objects.get_or_create(username=user)
                    allocation_user_obj, created = AllocationUser.objects.get_or_create(
                        user=user_obj,
                        allocation=allocation_obj,
                        status=AllocationUserStatusChoice.objects.get(name='Active')
                    )

                    if created:
                        allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read only')
                        allocation_user_obj.save()

            self.create_allocation_attribute(allocation_obj, 'GID', ldap_conn.get_group_gid_number(slate_project.get('namespace_entry')))
            self.create_allocation_attribute(allocation_obj, 'Namespace Entry', slate_project.get('namespace_entry'))
            self.create_allocation_attribute(allocation_obj, 'Allocated Quantity', slate_project.get('allocated_quantity'))

        print(f'Time elapsed: {time.time() - start_time}')
