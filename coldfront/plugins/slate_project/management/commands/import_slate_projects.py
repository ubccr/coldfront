import csv
import json
import datetime
import time
import ldap.filter
from ldap3 import Connection, Server

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
from coldfront.core.utils.common import import_from_settings


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--json", type=str)
        parser.add_argument("--out", type=str)
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

    def update_user_profile(self, user_obj, ldap_conn):
        attributes = ldap_conn.search_a_user(user_obj.username, ['title'])
        user_obj.userprofile.title = attributes.get('title')[0]
        user_obj.userprofile.save()

    def handle(self, *args, **kwargs):
        if not kwargs.get("json"):
            raise CommandError("JSON file does not exist")
        
        if not kwargs.get("out"):
            raise CommandError("Out file does not exist")
        
        slate_project_import_limit = kwargs.get("limit")
        if slate_project_import_limit is not None and slate_project_import_limit <= 0:
            raise CommandError("The limit must be > 0")

        print('Importing Slate Projects...')
        start_time = time.time()
        todays_date = datetime.date.today()
        file_name = kwargs.get("out")
        with open(kwargs.get("json"), 'r') as json_file:
            extra_information = json.load(json_file)
        slate_projects = []
        with open(file_name, 'r') as import_file:
            next(import_file)
            for line in import_file:
                line = line.strip('\n')
                line_split = line.split(',')

                extra_project_information = extra_information.get(line_split[0])
                if extra_project_information is None:
                    abstract = f'Slate Project {line_split[0]}'
                    project_title = f'Imported slate project {line_split[0]}'
                    allocated_quantity = None
                    start_date = None
                else:
                    abstract = extra_project_information.get('abstract')
                    project_title = extra_project_information.get('project_title')
                    allocated_quantity = extra_project_information.get('allocated_quantity')
                    start_date = extra_project_information.get('start_date')

                slate_project = {
                    "namespace_entry": line_split[0],
                    "ldap_group": line_split[1],
                    "owner_netid": line_split[2],
                    "gid_number": line_split[3],
                    "read_write_users": line_split[4].split(' '),
                    "read_only_users": line_split[5].split(' '),
                    "abstract": abstract,
                    "project_title": project_title,
                    "allocated_quantity": allocated_quantity,
                    "start_date": start_date
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

        ldap_conn = LDAPSearch()
        rejected_slate_projects = []
        for slate_project in slate_projects:
            user_obj, created = User.objects.get_or_create(username=slate_project.get('owner_netid'))
            if not created:
                self.update_user_profile(user_obj, ldap_conn)

            if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                rejected_slate_projects.append(slate_project.get('namespace_entry'))
                continue
            
            project_user_role = ProjectUserRoleChoice.objects.get(name='Manager')
            if user_obj.userprofile.title in ['Faculty', 'Staff', 'Academic (ACNP)', ]:
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

            read_write_users = slate_project.get('read_write_users')
            read_only_users = slate_project.get('read_only_users')
            all_users = read_write_users + read_only_users
            for user in all_users:
                enable_notifications = True
                if not user:
                    continue
                user_obj, created = User.objects.get_or_create(username=user)
                if not created:
                    self.update_user_profile(user_obj, ldap_conn)
                user_profile_obj = UserProfile.objects.get(user=user_obj)
                project_user_role = ProjectUserRoleChoice.objects.get(name='User')
                status = ProjectUserStatusChoice.objects.get(name='Active')
                if user_profile_obj.title == 'group':
                    project_user_role = ProjectUserRoleChoice.objects.get(name='Group')
                    enable_notifications = False

                if user_obj in [project_obj.pi, project_obj.requestor]:
                    project_user_role = ProjectUserRoleChoice.objects.get(name='Manager')

                if not user_profile_obj.title or user_profile_obj.title in ['Former Employee', 'Retired Staff']:
                    status = ProjectUserStatusChoice.objects.get(name='Inactive')

                ProjectUser.objects.get_or_create(
                    user=user_obj,
                    project=project_obj,
                    role=project_user_role,
                    enable_notifications=enable_notifications,
                    status=status
                )

            allocation_start_date = todays_date
            if slate_project.get('start_date'):
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
                status = AllocationUserStatusChoice.objects.get(name='Active')
                if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                    status = AllocationUserStatusChoice.objects.get(name='Inactive')
                allocation_user_obj, created = AllocationUser.objects.get_or_create(
                    user=user_obj,
                    allocation=allocation_obj,
                    status=status
                )
                if created:
                    allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                    allocation_user_obj.save()
            else:
                for user in read_write_users:
                    if not user:
                        continue
                    user_obj, created = User.objects.get_or_create(username=user)
                    status = AllocationUserStatusChoice.objects.get(name='Active')
                    if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                        status = AllocationUserStatusChoice.objects.get(name='Inactive')
                    allocation_user_obj, created = AllocationUser.objects.get_or_create(
                        user=user_obj,
                        allocation=allocation_obj,
                        status=status
                    )

                    if created:
                        allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                        allocation_user_obj.save()

                for user in read_only_users:
                    if not user:
                        continue
                    user_obj, created = User.objects.get_or_create(username=user)
                    status = AllocationUserStatusChoice.objects.get(name='Active')
                    if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                        status = AllocationUserStatusChoice.objects.get(name='Inactive')
                    allocation_user_obj, created = AllocationUser.objects.get_or_create(
                        user=user_obj,
                        allocation=allocation_obj,
                        status=status
                    )

                    if created:
                        allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read only')
                        allocation_user_obj.save()

            self.create_allocation_attribute(allocation_obj, 'GID', slate_project.get('gid_number'))
            self.create_allocation_attribute(allocation_obj, 'LDAP Group', slate_project.get('ldap_group'))
            self.create_allocation_attribute(allocation_obj, 'Namespace Entry', slate_project.get('namespace_entry'))
            if slate_project.get('allocated_quantity'):
                self.create_allocation_attribute(allocation_obj, 'Allocated Quantity', slate_project.get('allocated_quantity'))

        print(f'Slate projects not imported: {", ".join(rejected_slate_projects)}')
        print(f'Time elapsed: {time.time() - start_time}')


class LDAPSearch():
    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_USER_SEARCH_CONNECT_TIMEOUT', 2.5)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

    def search_a_user(self, user_search_string, search_attributes_list=None):
        # Add check if debug is true to run this. If debug is not then write an error to log file.
        assert type(search_attributes_list) is list, 'search_attributes_list should be a list'

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': ldap.filter.filter_format("(cn=%s)", [user_search_string]),
                            'attributes': search_attributes_list,
                            'size_limit': 1}
        self.conn.search(**searchParameters)
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = dict.fromkeys(search_attributes_list, [''])

        return attributes