from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeUsage
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile


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
    if data.get('only_search_projects'):
        queryset = build_project_queryset(data, get_request)
        columns = build_project_columns(data)
        project_users = get_project_users(data, queryset, columns)
        rows = build_project_rows(columns, queryset, project_users)
        return rows, columns
    
    queryset = build_queryset(data, allocationattribute_data, get_request)
    columns = build_columns(data, allocationattribute_data)
    additional_data = get_allocation_attribute_data(allocationattribute_data)
    additional_usage_data = get_allocation_attribute_usage(additional_data)
    allocation_users = get_allocation_users(data, queryset, columns)
    rows = build_rows(columns, queryset, additional_data, additional_usage_data, allocation_users)

    return rows, columns

def get_allocation_users(data, queryset, columns):
    column_field_names = [column.get('field_name') for column in columns]
    allocation_users = {}
    if 'allocation__users' in column_field_names:
        user_profile_objs = UserProfile.objects.prefetch_related('user').all()
        if 'user_profile__department' in column_field_names or 'user_profile__title' in column_field_names:
            title = data.get('user_profile__title')
            department = data.get('user_profile__department')
            if title:
                user_profile_objs = user_profile_objs.filter(title__icontains=title)
            if department:
                user_profile_objs = user_profile_objs.filter(department__icontains=department)
        for allocation_obj in queryset:
            all_allocation_users = allocation_obj.allocationuser_set.all()
            users = all_allocation_users.values_list('user', flat=True)
            allocation_users[allocation_obj.id] = user_profile_objs.filter(user__in=users)

    return allocation_users

def build_columns(data, allocationattribute_data):
    """
    Creates the columns for the table. If a field containing 'display' has been selected then a new
    column is created for the corresponding data.

    Params:
        data (dict): Contains all the fields in the search form.
        allocationattribute_data (dict): Contains all the fields in the allocation attribute forms.

    Returns:
        list[dict]: entries for each column of the format:

        {'display_name': str, 'field_name': str}

        if the data is from an allocation attribute form the dictionary has an additional entry:

        { 'id': int } # ID of allocation attribute type in the allocation attribute
    """
    only_projects = data.get('only_search_projects')

    columns = []
    for key, value in data.items():
        if 'display' in key and value:
            if not only_projects:
                if key == 'display__project__users':
                    continue

                if key in ['display__user_profile__department', 'display__user_profile__title']:
                    if not data.get('display__allocation__users'):
                        continue

            display_name = ' '.join(key.split('__')[1:])
            display_name = ' '.join(display_name.split('_'))
            field_name = key[len('display') + 2:]
            columns.append({
                'display_name': display_name.title(),
                'field_name': field_name
            })

    for entry in allocationattribute_data:
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

    return columns

def build_rows(columns, queryset, additional_data, additional_usage_data, allocation_users):
    """
    Creates the rows for the table. Rows are the length of the number of columns. The length of the
    Queryset is the number of rows.

    Params:
        columns (dict): Columns in the table.
        queryset (QuerySet): Allocation queryset to grab the information from.

    Returns:
        dict: Each entry is a row in the format:

        {'row number': [column 1 data, column 2 data, ...], ...}
    """
    rows_dict = {}
    cache = {'total_project_users': {}, 'total_allocation_users': {}}
    row_idx = 0
    if len(allocation_users) > 0:
        for allocation_obj in queryset:
            user_profiles = allocation_users.get(allocation_obj.id)
            for user_profile in user_profiles:
                row, cache = build_row(
                    allocation_obj,
                    columns,
                    cache,
                    additional_data,
                    additional_usage_data,
                    user_profile=user_profile,
                    username=user_profile.user.username
                )
                rows_dict[row_idx] = row
                row_idx += 1

    else:
        for allocation_obj in queryset:
            row, cache = build_row(
                allocation_obj,
                columns,
                cache,
                additional_data,
                additional_usage_data
            )
            rows_dict[row_idx] = row
            row_idx += 1

    return rows_dict

def build_row(allocation_obj, columns, cache, additional_data, additional_usage_data, user_profile=None, username=None):
    row = []
    for column in columns:
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
        elif model == 'user_profile':
            model = user_profile

        if model is not None:
            current_attribute = model
            for attribute in attributes:
                if hasattr(current_attribute, attribute):
                    current_attribute = getattr(current_attribute, attribute)
                    continue

                if 'project__total_users' == field_name:
                    current_attribute = cache['total_project_users'].get(model.id)
                    if current_attribute is None:
                        all_project_users = model.projectuser_set.all()
                        filtered_project_users_count = 0
                        for project_user in all_project_users:
                            if project_user.status.name == 'Active':
                                filtered_project_users_count += 1
                        current_attribute = filtered_project_users_count
                        cache['total_project_users'][model.id] = current_attribute
                    break

                if 'allocation__total_users' == field_name:
                    current_attribute = cache['total_allocation_users'].get(model.id)
                    if current_attribute is None:
                        all_allocation_users = model.allocationuser_set.all()
                        filtered_allocation_users_count = 0
                        for allocation_user in all_allocation_users:
                            if allocation_user.status.name == 'Active':
                                filtered_allocation_users_count += 1
                        current_attribute = filtered_allocation_users_count
                        cache['total_allocation_users'][model.id] = current_attribute
                    break

                if 'allocation__users' == field_name:
                    current_attribute = username
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
        row.append(current_attribute)

    return row, cache

def build_queryset(data, allocationattribute_data, request):
    """
    Creates an allocation queryset.

    Params:
        allocationattribute_data (dict): Information filled out on the allocation attribute search form.
        request (dict): GET request sent by the server.

    Returns:
        QuerySet: Allocation queryset.
    """
    allocation_queryset = build_allocation_queryset(data, request)

    project_queryset = build_project_queryset(data, request)
    allocation_queryset = allocation_queryset.filter(project__in=list(project_queryset))

    resource_queryset = build_resource_queryset(data)
    allocation_queryset = allocation_queryset.filter(resources__in=list(resource_queryset))

    allocation_queryset = filter_by_allocation_attribute_parameters(allocationattribute_data, allocation_queryset)
    
    return allocation_queryset

def filter_by_allocation_attribute_parameters(allocationattribute_data, allocation_queryset):
    """
    Filters the allocation queryset base on provided allocation attribute data.

    Params:
        allocationattribute_data (dict): Information filled out on the allocation attribute search form.
        allocation_queryset (QuerySet): Allocation queryset.

    Returns:
        QuerySet: Allocation queryset.
    """
    for entry in allocationattribute_data:
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

def get_allocation_attribute_data(data):
    """
    Grabs the desired information on the selected allocation attributes.

    Params:
        data (list[dict]): Fields filled out in each allocation attribute form.

    Returns:
        dict: Allocation attribute information with the format:

        {allocation_id: [allocation attribute object, ...], ...}
    """
    all_allocation_attributes = {}
    for entry in data:
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

def get_allocation_attribute_usage(data):
    """
    Grabs the usage data on the selected allocation attributes if applicable.

    Params:
        data (dict): Fields filled out in each allocation attribute form.

    Returns:
        dict: Allocation attribute usage numbers with the format:

        { allocation_id: [allocation attribute usage number, ...], ...}
    """
    all_allocation_attribute_usages = {}
    allocation_attributes = [
        allocation_attribute 
        for allocation_attributes in data.values() 
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

def build_allocation_queryset(data, request):
    """
    Creates an allocation queryset.

    Params:
        data (dict): Information filled out on the search form.
        request (dict): GET request sent by the server.

    Returns:
        QuerySet: Allocation queryset.
    """
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
            allocationuser__status__name='Active'
        )

    if data.get('allocation__status__name'):
        allocations = allocations.filter(
            status__in=data.get('allocation__status__name')
        )

    return allocations

def build_resource_queryset(data):
    """
    Creates a resource queryset.

    Params:
        data (dict): Information filled out on the search form.

    Returns:
        QuerySet: Resource queryset.
    """
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

def get_project_users(data, queryset, columns):
    column_field_names = [column.get('field_name') for column in columns]
    project_users = {}
    if 'project__users' in column_field_names:
        user_profile_objs = UserProfile.objects.prefetch_related('user').all()
        if 'user_profile__department' in column_field_names or 'user_profile__title' in column_field_names:
            title = data.get('user_profile__title')
            department = data.get('user_profile__department')
            if title:
                user_profile_objs = user_profile_objs.filter(title__icontains=title)
            if department:
                user_profile_objs = user_profile_objs.filter(department__icontains=department)
        for project_obj in queryset:
            all_project_users = project_obj.projectuser_set.all()
            users = all_project_users.values_list('user', flat=True)
            project_users[project_obj.id] = user_profile_objs.filter(user__in=users)

    return project_users
    
def build_project_queryset(data, request):
    """
    Creates a project queryset.

    Params:
        data (dict): Information filled out on the search form.
        request (dict): GET request sent by the server.

    Returns:
        QuerySet: Project queryset.
    """
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

    return projects

def build_project_columns(data):
    """
    Creates the columns for the projects table. If a field containing 'display' has been selected
    then a new column is created for the corresponding data.

    Params:
        data (dict): Contains all the fields in the search form.

    Returns:
        list[dict]: entries for each column of the format:

        {'display_name': str, 'field_name': str}
    """
    columns = []
    for key, value in data.items():
        if 'display' in key and ('project' in key or 'user_profile' in key) and value:
            if key in ['display__user_profile__department', 'display__user_profile__title']:
                if not data.get('display__project__users'):
                    continue
            display_name = ' '.join(key.split('_')[1:])
            field_name = key[len('display') + 2:]
            columns.append({
                'display_name': display_name.title(),
                'field_name': field_name
            })

    return columns

def build_project_rows(columns, queryset, project_users):
    """
    Creates the rows for the projects table. Rows are the length of the number of columns. The
    length of the Queryset is the number of rows.

    Params:
        columns (dict): Columns in the table.
        queryset (QuerySet): Project queryset to grab the information from.

    Returns:
        dict: Each entry is a row in the format:

        {'row number': [column 1 data, column 2 data, ...], ...}
    """
    column_field_names = [column.get('field_name') for column in columns]
    rows_dict = {}
    row_idx = 0
    if len(project_users) > 0:
        for project_obj in queryset:
            user_profiles = project_users.get(project_obj.id)
            for user_profile in user_profiles:
                row = build_project_row(
                    project_obj,
                    column_field_names,
                    user_profile=user_profile,
                    username=user_profile.user.username
                )
                rows_dict[row_idx] = row
                row_idx += 1
    else:
        for project_obj in queryset:
            row = build_project_row(project_obj, column_field_names)
            rows_dict[row_idx] = row
            row_idx += 1

    return rows_dict

def build_project_row(project_obj, columns, user_profile=None, username=None):
    row = []
    for column in columns:
        attributes = column.split('__')[1:]

        current_attribute = project_obj
        for attribute in attributes:
            if 'user_profile' in column:
                current_attribute = user_profile

            if hasattr(current_attribute, attribute):
                current_attribute = getattr(current_attribute, attribute)
                continue

            if 'project__total_users' in column:
                all_project_users = project_obj.projectuser_set.all()
                filtered_project_users_count = 0
                for project_user in all_project_users:
                    if project_user.status.name == 'Active':
                        filtered_project_users_count += 1
                current_attribute = filtered_project_users_count

            elif 'project__users' in column:
                current_attribute = username

        if current_attribute is None:
            current_attribute = ''

        row.append(current_attribute)

    return row