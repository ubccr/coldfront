import datetime
from django.contrib.auth.models import User

from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttribute,
                                              AllocationAttributeUsage,
                                              AllocationUser)
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile


class ProjectTable:
    def __init__(self, data):
        self.project_queryset = None
        self.columns = []
        self.rows = {}
        self.data = data

    def get_project_queryset(self):
        """
        Creates a project queryset.

        Params:
            data (dict): Information filled out on the search form.
            request (dict): GET request sent by the server.

        Returns:
            QuerySet: Project queryset.
        """
        data = self.data
        projects = Project.objects.prefetch_related(
            'pi',
            'requestor',
            'status',
            'type',
            'projectuser_set',
            'projectuser_set__status',
            'projectuser_set__user'
        ).all().order_by('id')

        if data.get('project__title'):
            projects = projects.filter(title__icontains= data.get('project__title'))
        if data.get('project__description'):
            projects = projects.filter(description__icontains= data.get('project__description'))
        if data.get('project__pi__username'):
            projects = projects.filter(pi__username__icontains= data.get('project__pi__username'))
        if data.get('project__requestor__username'):
            projects = projects.filter(
                requestor__username__icontains= data.get('project__requestor__username')
            )
        if data.get('project__status__name'):
            projects = projects.filter(status__in= data.get('project__status__name'))
        if data.get('project__type__name'):
            projects = projects.filter(type__in= data.get('project__type__name'))
        if data.get('project__class_number'):
            projects = projects.filter(class_number__icontains= data.get('project__class_number'))
        if data.get('project__user_username'):
            projects = projects.filter(
                projectuser__user__username__icontains=data.get('project__user_username'),
                projectuser__status__name='Active'
            )
        if data.get('projects_using_ai'):
            projects = projects.filter(
                allocation__allocationattribute__allocation_attribute_type__name='Has DL Workflow',
                allocation__allocationattribute__value='Yes',
                allocation__status__name='Active'
            ).distinct()
        if data.get('project__created_after_date'):
            projects = projects.filter(created__gt=data.get('project__created_after_date'))
        if data.get('project__created_before_date'):
            projects = projects.filter(created__lt=data.get('project__created_before_date'))
        if data.get('project__end_date'):
            projects = projects.filter(end_date=data.get('project__end_date'))

        self.project_queryset = projects

    def build_row(self, project_obj):
        row = []
        for column in self.columns:
            attributes = column.get('field_name').split('__')[1:]
            current_attribute = project_obj
            for attribute in attributes:
                if hasattr(current_attribute, attribute):
                    current_attribute = getattr(current_attribute, attribute)
                    continue

                if 'project__total_users' == column.get('field_name'):
                    # Need to do all() or prefetch doesn't work and we end up running more queries
                    all_project_users = project_obj.projectuser_set.all()
                    filtered_project_users_count = 0
                    for project_user in all_project_users:
                        if project_user.status.name == 'Active':
                            filtered_project_users_count += 1
                    current_attribute = filtered_project_users_count

                elif 'project__users' in column.get('field_name'):
                    all_project_users = project_obj.projectuser_set.all()
                    filtered_project_users = []
                    for project_user in all_project_users:
                        if project_user.status.name == 'Active':
                            filtered_project_users.append(project_user.user.username)
                    current_attribute = ', '.join(filtered_project_users)

                elif 'project__resources' in column.get('field_name'):
                    all_project_allocations = project_obj.allocation_set.filter(
                        status__name__in=['Active', 'Renewal Requested'])
                    resource_list = []
                    for project_allocation in all_project_allocations:
                        resource_list.append(f'{project_allocation.get_parent_resource.name} ({project_allocation.pk})')
                    current_attribute = ', '.join(resource_list)

            if current_attribute is None:
                current_attribute = ''

            if type(current_attribute) in [datetime.datetime, datetime.date]:
                current_attribute = current_attribute.isoformat()
            
            row.append(current_attribute)
        return row

    def build_rows(self):
        rows = {}
        for idx, project_obj in enumerate(self.project_queryset):
            rows[idx] = self.build_row(project_obj)
        self.rows = rows

    def build_columns(self):
        data = self.data
        columns = []
        for key, value in data.items():
            if 'display' in key and value:
                display_name = ' '.join(key.split('_')[1:])
                field_name = key[len('display') + 2:]
                columns.append({
                    'display_name': display_name.title(),
                    'field_name': field_name
                })

        self.columns = columns

    def build_table(self):
        self.get_project_queryset()
        self.build_columns()
        self.build_rows()
        return self.rows, self.columns
    

class AllocationTable:
    def __init__(self, form_data, allocation_attribute_form_data):
        self.allocation_queryset = None
        self.allocation_attribute_queryset = None
        self.columns = []
        self.rows = {}
        self.form_data = form_data
        self.allocation_attribute_form_data = allocation_attribute_form_data

    def build_allocation_queryset(self):
        allocation_queryset = self.get_allocation_queryset()

        project_queryset = self.get_project_queryset()
        allocation_queryset = allocation_queryset.filter(project__in=list(project_queryset))

        resource_queryset = self.get_resource_queryset()
        allocation_queryset = allocation_queryset.filter(resources__in=list(resource_queryset))

        allocation_queryset = self.filter_by_allocation_attribute_parameters(allocation_queryset)
        self.allocation_queryset = allocation_queryset
    
    def get_allocation_queryset(self):
        data = self.form_data
        allocations = Allocation.objects.prefetch_related(
            'project',
            'project__pi',
            'project__requestor',
            'project__status',
            'project__type',
            'project__projectuser_set',
            'project__projectuser_set__status',
            'allocationuser_set',
            'allocationuser_set__status',
            'allocationuser_set__user',
            'status',
            'resources',
            'resources__resource_type'
        ).all().order_by('project__id')

        if data.get('allocation__user_username'):
            allocations = allocations.filter(
                allocationuser__user__username__icontains=data.get('allocation__user_username'),
                allocationuser__status__name__in=['Active', 'Invited', 'Pending', 'Disabled', 'Retired']
            )

        if data.get('allocation__status__name'):
            allocations = allocations.filter(
                status__in=data.get('allocation__status__name')
            )

        if data.get('allocation__created_after_date'):
            allocations = allocations.filter(
                created__gt=data.get('allocation__created_after_date')
            )
        if data.get('allocation__created_before_date'):
            allocations = allocations.filter(
                created__lt=data.get('allocation__created_before_date')
            )

        return allocations
    
    def get_project_queryset(self):
        data = self.form_data
        projects = Project.objects.prefetch_related(
            'pi',
            'requestor',
            'status',
            'type',
            'projectuser_set',
            'projectuser_set__status',
            'projectuser_set__user'
        ).all().order_by('id')

        if data.get('project__title'):
            projects = projects.filter(title__icontains= data.get('project__title'))
        if data.get('project__description'):
            projects = projects.filter(description__icontains= data.get('project__description'))
        if data.get('project__pi__username'):
            projects = projects.filter(pi__username__icontains= data.get('project__pi__username'))
        if data.get('project__requestor__username'):
            projects = projects.filter(
                requestor__username__icontains= data.get('project__requestor__username')
            )
        if data.get('project__status__name'):
            projects = projects.filter(status__in= data.get('project__status__name'))
        if data.get('project__type__name'):
            projects = projects.filter(type__in= data.get('project__type__name'))
        if data.get('project__class_number'):
            projects = projects.filter(class_number__icontains= data.get('project__class_number'))
        if data.get('project__user_username'):
            projects = projects.filter(
                projectuser__user__username__icontains=data.get('project__user_username'),
                projectuser__status__name='Active'
            )
        if data.get('project__created_after_date'):
            projects = projects.filter(created__gt=data.get('project__created_after_date'))
        if data.get('project__created_before_date'):
            projects = projects.filter(created__lt=data.get('project__created_before_date'))
        if data.get('project__end_date'):
            projects = projects.filter(end_date=data.get('project__end_date'))

        return projects

    def get_resource_queryset(self):
        data = self.form_data
        resources = Resource.objects.prefetch_related('resource_type',).filter(is_allocatable=True)

        if data.get('resources__name'):
            resources = resources.filter(
                id__in=data.get('resources__name').values_list('id')
            )
        if data.get('resources__resource_type__name'):
            resources = resources.filter(
                resource_type__in=data.get('resources__resource_type__name')
            )

        return resources

    def filter_by_allocation_attribute_parameters(self, allocation_queryset):
        for entry in self.allocation_attribute_form_data:
            allocation_attribute_type = entry.get('allocationattribute__name')
            allocation_attribute_value = entry.get('allocationattribute__value')
            allocation_attribute_has_usage = entry.get('allocationattribute__has_usage')
            if allocation_attribute_has_usage is not None:
                allocation_attribute_has_usage = int(entry.get('allocationattribute__has_usage'))
            allocation_attribute_usage = entry.get('allocationattribute__usage')
            allocation_attribute_equality = entry.get('allocationattribute__equality')
            allocation_attribute_usage_format = entry.get('allocationattribute__usage_format')

            if allocation_attribute_type and allocation_attribute_value:
                allocation_queryset = allocation_queryset.filter(
                    allocationattribute__allocation_attribute_type=allocation_attribute_type,
                    allocationattribute__value__icontains=allocation_attribute_value
                )

            if allocation_attribute_type and allocation_attribute_has_usage and allocation_attribute_usage:
                allocation_queryset = allocation_queryset.filter(
                    allocationattribute__allocation_attribute_type=allocation_attribute_type
                )
                if allocation_attribute_usage_format == 'whole':
                    if allocation_attribute_equality == 'lt':
                        allocation_queryset = allocation_queryset.filter(
                            allocationattribute__allocationattributeusage__value__lt=allocation_attribute_usage
                        )
                    elif allocation_attribute_equality == 'gt':
                        allocation_queryset = allocation_queryset.filter(
                            allocationattribute__allocationattributeusage__value__gt=allocation_attribute_usage
                        )
                elif allocation_attribute_usage_format == 'percent':
                    allocation_attribute_ids = allocation_queryset.values_list(
                        'allocationattribute__allocationattributeusage', flat=True
                    )
                    allocation_attribute_ids = [
                        allocation_attribute_id 
                        for allocation_attribute_id in allocation_attribute_ids 
                        if allocation_attribute_id is not None
                    ]
                    allocation_attribute_usages = AllocationAttributeUsage.objects.filter(
                        allocation_attribute__id__in=allocation_attribute_ids
                    )
                    remaining_entries = []
                    for allocation_attribute_usage_result in allocation_attribute_usages:
                        allocation_attribute_obj = allocation_attribute_usage_result.allocation_attribute
                        allocation_attribute_value_with_usage = float(allocation_attribute_obj.value)
                        allocation_attribute_usage_value = allocation_attribute_usage_result.value

                        fraction = allocation_attribute_usage_value / allocation_attribute_value_with_usage * 100
                        if allocation_attribute_equality == 'lt' and fraction < allocation_attribute_usage:
                            remaining_entries.append(allocation_attribute_obj.id)
                        elif allocation_attribute_equality == 'gt' and fraction > allocation_attribute_usage:
                            remaining_entries.append(allocation_attribute_obj.id)

                    allocation_queryset = allocation_queryset.filter(
                        allocationattribute__id__in = remaining_entries
                    )

        return allocation_queryset
    
    def build_columns(self):
        columns = []
        for key, value in self.form_data.items():
            if 'display' in key and value:
                display_name = ' '.join(key.split('__')[1:])
                display_name = ' '.join(display_name.split('_'))
                field_name = key[len('display') + 2:]
                columns.append({
                    'display_name': display_name.title(),
                    'field_name': field_name
                })

        for entry in self.allocation_attribute_form_data:
            allocation_attribute_type = entry.get('allocationattribute__name')
            if allocation_attribute_type:
                display_name = allocation_attribute_type.name
                field_name = 'allocationattribute__name'
                columns.append({
                    'display_name': display_name,
                    'field_name': field_name,
                    'id': allocation_attribute_type.id
                })

                has_usage = int(entry.get('allocationattribute__has_usage'))
                if has_usage and int(has_usage):
                    display_name += ' Usage'
                    field_name = 'allocationattribute__has_usage'
                    columns.append({
                        'display_name': display_name,
                        'field_name': field_name,
                        'id': allocation_attribute_type.id
                    })

            self.columns = columns

    def build_rows(self, additional_data, additional_usage_data):
        rows_dict = {}
        for idx, allocation_obj in enumerate(self.allocation_queryset):
            row = self.build_row(
                allocation_obj,
                additional_data,
                additional_usage_data
            )
            rows_dict[idx] = row

        self.rows = rows_dict

    def build_row(self, allocation_obj, additional_data, additional_usage_data):
        row = []
        for column in self.columns:
            field_name = column.get('field_name')
            split = field_name.split('__')
            model = split[0]
            attributes = split[1:]
            if model == 'allocation':
                model = allocation_obj
            elif model == 'project':
                model = getattr(allocation_obj, model)
            elif model == 'resources':
                model = allocation_obj.get_parent_resource
            elif model == 'allocationattribute':
                model = None

            if model is not None:
                current_attribute = model
                for attribute in attributes:
                    if hasattr(current_attribute, attribute):
                        current_attribute = getattr(current_attribute, attribute)
                        continue

                    if 'project__total_users' == field_name:
                        # Need to do all() or prefetch doesn't work and we end up running more queries
                        all_project_users = model.projectuser_set.all()
                        filtered_project_users_count = 0
                        for project_user in all_project_users:
                            if project_user.status.name == 'Active':
                                filtered_project_users_count += 1
                        current_attribute = filtered_project_users_count
                        break

                    if 'allocation__total_users' == field_name:
                        all_allocation_users = model.allocationuser_set.all()
                        filtered_allocation_users_count = 0
                        for allocation_user in all_allocation_users:
                            if allocation_user.status.name in ['Active', 'Invited', 'Pending', 'Disabled', 'Retired']:
                                filtered_allocation_users_count += 1
                        current_attribute = filtered_allocation_users_count
                        break

                    if 'allocation__users' == field_name:
                        all_allocation_users = model.allocationuser_set.all()
                        filtered_allocation_users = []
                        for allocation_user in all_allocation_users:
                            if allocation_user.status.name in ['Active', 'Invited', 'Pending', 'Disabled', 'Retired']:
                                filtered_allocation_users.append(allocation_user.user.username)
                        current_attribute = ', '.join(filtered_allocation_users)
                        break

            else:
                allocation_id = allocation_obj.id
                value = ''
                attribute = attributes[0]
                if attribute == 'name':
                    allocation_attributes = additional_data.get(allocation_id)
                    if allocation_attributes is not None:
                        for allocation_attribute in allocation_attributes:
                            # Assumes no duplicate allocation attribute types in list
                            if allocation_attribute.allocation_attribute_type.id == column.get('id'):
                                value = allocation_attribute.value
                                break
                elif attribute == 'has_usage':
                    allocation_attribute_usages = additional_usage_data.get(allocation_id)
                    if allocation_attribute_usages is not None:
                        for allocation_attribute_usage in allocation_attribute_usages:
                            # Assumes no duplicate allocation attribute types in list
                            if allocation_attribute_usage.allocation_attribute.allocation_attribute_type.id == column.get('id'):
                                value = allocation_attribute_usage.value
                                break

                current_attribute = value

            if current_attribute is None:
                current_attribute = ""

            if type(current_attribute) in [datetime.datetime, datetime.date]:
                current_attribute = current_attribute.isoformat()

            row.append(current_attribute)

        return row

    def get_allocation_attribute_data(self):
        all_allocation_attributes = {}
        for entry in self.allocation_attribute_form_data:
            allocation_attribute_type = entry.get('allocationattribute__name')
            if allocation_attribute_type:
                allocation_attributes = AllocationAttribute.objects.prefetch_related(
                    'allocation', 'allocation_attribute_type'
                ).filter(allocation_attribute_type=allocation_attribute_type)
                for allocation_attribute in allocation_attributes:
                    if all_allocation_attributes.get(allocation_attribute.allocation.id) is None:
                        all_allocation_attributes[allocation_attribute.allocation.id] = [
                            allocation_attribute
                        ]
                    else:
                        all_allocation_attributes[allocation_attribute.allocation.id].append(
                            allocation_attribute
                        )

        return all_allocation_attributes

    def get_allocation_attribute_usage(self, additional_data):
        all_allocation_attribute_usages = {}
        allocation_attributes = [
            allocation_attribute 
            for allocation_attributes in additional_data.values() 
            for allocation_attribute in allocation_attributes
        ]
        allocation_attribute_usages = AllocationAttributeUsage.objects.prefetch_related(
            'allocation_attribute'
        ).filter(allocation_attribute__in=allocation_attributes)
        for allocation_attribute_usage in allocation_attribute_usages:
            allocation_attribute = allocation_attribute_usage.allocation_attribute
            if all_allocation_attribute_usages.get(allocation_attribute.id) is None:
                all_allocation_attribute_usages[allocation_attribute.allocation.id] = [
                    allocation_attribute_usage
                ]
            else:
                all_allocation_attribute_usages[allocation_attribute.allocation.id].append(
                    allocation_attribute_usage
                )

        return all_allocation_attribute_usages

    def build_table(self):
        self.build_allocation_queryset()
        self.build_columns()
        additional_data = self.get_allocation_attribute_data()
        additional_usage_data = self.get_allocation_attribute_usage(additional_data)
        self.build_rows(additional_data, additional_usage_data)

        return self.rows, self.columns


class UserTable:
    def __init__(self, data):
        self.data = data
        self.rows = {}
        self.columns = []
        self.user_queryset = None

    def build_user_queryset(self):
        user_queryset = self.get_user_queryset()

        user_profile_queryset = self.get_user_profile_querset()
        user_queryset = user_queryset.filter(userprofile__in=user_profile_queryset)

        self.user_queryset = user_queryset

    def get_user_queryset(self):
        data = self.data
        users = User.objects.prefetch_related(
            'userprofile'
        )
        if data.get('user__type') == 'project':
            project_usernames = set(ProjectUser.objects.filter(
                status__name='Active',
                project__status__name='Active'
            ).values_list('user__username', flat=True))
            users = users.filter(username__in=project_usernames)
        elif data.get('user__type') == 'allocation':
            allocation_usernames = set(AllocationUser.objects.filter(
                status__name__in=['Active', 'Invited', 'Pending', 'Disabled', 'Retired'],
                allocation__status__name='Active',
                allocation__project__status__name='Active'
            ).values_list('user__username', flat=True))
            users = users.filter(username__in=allocation_usernames)

        if data.get('user__usernames'):
            usernames = data.get('user__usernames').split(',')
            usernames = [username.strip() for username in usernames]
            users = users.filter(username__in=usernames)
        if data.get('user__first_name'):
            users = users.filter(first_name=data.get('user__first_name'))
        if data.get('user__last_name'):
            users = users.filter(last_name=data.get('user__last_name'))

        return users

    def get_user_profile_querset(self):
        data = self.data
        user_profiles = UserProfile.objects.all()

        if data.get('user__userprofile__title'):
            user_profiles = user_profiles.filter(title__icontains=data.get('user__userprofile__title'))
        if data.get('user__userprofile__department'):
            user_profiles = user_profiles.filter(department__icontains=data.get('user__userprofile__department'))

        return user_profiles
    
    def build_columns(self):
        data = self.data
        columns = []
        for key, value in data.items():
            if 'display' in key and value:
                display_name = ' '.join(key.split('_')[1:])
                field_name = key[len('display') + 2:]
                columns.append({
                    'display_name': display_name.title(),
                    'field_name': field_name
                })

        self.columns = columns

    def build_rows(self):
        rows = {}
        for idx, user_obj in enumerate(self.user_queryset):
            rows[idx] = self.build_row(user_obj)
        self.rows = rows

    def build_row(self, user_obj):
        row = []
        for column in self.columns:
            attributes = column.get('field_name').split('__')[1:]
            current_attribute = user_obj
            for attribute in attributes:
                if hasattr(current_attribute, attribute):
                    current_attribute = getattr(current_attribute, attribute)
                    continue

                if attribute == 'total_projects':
                    current_attribute = ProjectUser.objects.filter(
                        user=user_obj, status__name='Active', project__status__name='Active'
                    ).count()
                if attribute == 'total_pi_projects':
                    current_attribute = ProjectUser.objects.filter(
                        user=user_obj,
                        project__pi=user_obj,
                        status__name='Active',
                        project__status__name='Active'
                    ).count()
                if attribute == 'total_manager_projects':
                    current_attribute = ProjectUser.objects.filter(
                        user=user_obj,
                        role__name='Manager',
                        status__name='Active',
                        project__status__name='Active'
                    ).count()
                if attribute == 'total_allocations':
                    current_attribute = AllocationUser.objects.filter(
                        user=user_obj,
                        status__name__in=['Active', 'Invited', 'Pending', 'Disabled', 'Retired'],
                        allocation__status__name='Active',
                        allocation__project__status__name='Active'
                    ).count()

            if current_attribute is None:
                current_attribute = ''
            row.append(current_attribute)
        return row

    def build_table(self):
        self.build_user_queryset()
        self.build_columns()
        self.build_rows()

        return self.rows, self.columns

def build_table(data, allocationattribute_data, get_request):
    """
    Creates a the rows and columns for the table.

    Params:
        allocationattribute_data (dict): Information filled out on the allocation attribute search form.
        request (dict): GET request sent by the server.

    Returns:
        rows (dict): Rows of the table.
        columns (list): Columns of the table.
    """
    if data.get('current_tab') == 2:
        user_table = UserTable(data)
        return user_table.build_table()

    if data.get('current_tab') == 1:
        if data.get('only_search_projects'):
            project_table = ProjectTable(data)
            return project_table.build_table()

        allocation_table = AllocationTable(data, allocationattribute_data)
        return allocation_table.build_table()
