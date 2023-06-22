from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation, AllocationAttribute
from coldfront.core.resource.models import Resource

from django.contrib import messages
from django.utils.html import format_html
from django.http import QueryDict


def build_table( data, allocationattribute_data, get_request):
    if data.get('only_search_projects'):
        queryset = build_project_queryset(data, get_request)
        columns = build_project_columns(data)
        rows = build_project_rows(columns, queryset)
        return rows, columns
    
    queryset = build_queryset(data, allocationattribute_data, get_request)
    columns = build_columns(data, allocationattribute_data)
    additional_data = get_allocation_attribute_data(allocationattribute_data)
    rows = build_rows(columns, queryset, additional_data)

    return rows, columns

def build_columns(data, allocationattribute_data):
    columns = []
    for key, value in data.items():
        if 'display' in key and value:
            display_name = ' '.join(key.split('__')[1:])
            field_name = key[len('display') + 2:]
            enable_sorting = 'false'
            if 'title' in field_name or 'description' in field_name:
                enable_sorting = 'false'
            columns.append({
                'enable_sorting': enable_sorting,
                'display_name': display_name.title(),
                'field_name': field_name
            })

    for entry in allocationattribute_data:
        key = entry.get('allocationattribute__name')
        if key:
            display_name = key.name
            field_name = 'allocationattribute__name'
            enable_sorting = 'false'
            columns.append({
                'enable_sorting': enable_sorting,
                'display_name': display_name,
                'field_name': field_name,
                'id': key.id
            })

    return columns

def build_rows(columns, queryset, additional_data):
    rows_dict = {}
    for i, result in enumerate(queryset):
        rows_dict[i] = []

        for column in columns:
            field_name = column.get('field_name')
            if 'allocationattribute' in field_name:
                allocation_id = result.id
                allocation_attributes = additional_data.get(allocation_id)
                if allocation_attributes is not None:
                    value = ''
                    for allocation_attribute in allocation_attributes:
                        if allocation_attribute.allocation_attribute_type.id == column.get('id'):
                            value = allocation_attribute.value
                            break
                else:
                    value = ''
                rows_dict[i].append(value)
                continue

            split = field_name.split('__')
            nested_attribute = ""
            if len(split) == 3:
                model, attribute, nested_attribute = split
            else:
                model, attribute = split

            if 'project' == model:
                project = getattr(result, model)
                attribute = getattr(project, attribute)
            elif 'resources' == model:
                resource = result.get_parent_resource
                # if attribute == 'type':
                #     attribute = 'resource_type'
                attribute = getattr(resource, attribute)
            else:
                attribute = getattr(result, attribute)

            if nested_attribute:
                attribute = getattr(attribute, nested_attribute)
            if attribute is None:
                attribute = ""
            rows_dict[i].append(attribute)

    return rows_dict

def build_queryset(data, allocationattribute_data, request):
    allocation_queryset = build_allocation_queryset(data, request)

    project_queryset = build_project_queryset(data, request)
    allocation_queryset = allocation_queryset.filter(project__in=list(project_queryset))

    resource_queryset = build_resource_queryset(data)
    allocation_queryset = allocation_queryset.filter(resources__in=list(resource_queryset))

    allocation_queryset = filter_by_allocation_attribute_parameters(allocationattribute_data, allocation_queryset)
    
    return allocation_queryset

def filter_by_allocation_attribute_parameters(allocationattribute_data, allocation_queryset):
    for entry in allocationattribute_data:
        allocation_attribute_type = entry.get('allocationattribute__name')
        allocation_attribute_value = entry.get('allocationattribute__value')
        if allocation_attribute_type and allocation_attribute_value:
            allocation_queryset = allocation_queryset.filter(
                allocationattribute__allocation_attribute_type=allocation_attribute_type,
                allocationattribute__value__icontains=allocation_attribute_value
            )

    return allocation_queryset

def get_allocation_attribute_data(data):
    all_allocation_attributes = {}
    for entry in data:
        allocation_attribute_type = entry.get('allocationattribute__name')
        if allocation_attribute_type:
            allocation_attributes = AllocationAttribute.objects.filter(allocation_attribute_type=allocation_attribute_type)
            for allocation_attribute in allocation_attributes:
                if all_allocation_attributes.get(allocation_attribute.allocation.id) is None:
                    all_allocation_attributes[allocation_attribute.allocation.id] = [allocation_attribute]
                else:
                    all_allocation_attributes[allocation_attribute.allocation.id].append(allocation_attribute)

    return all_allocation_attributes

def build_allocation_queryset(data, request):
    order_by = request.get('order_by')
    if order_by:
        direction = request.get('direction')
        if direction == 'asc':
            direction = ''
        else:
            direction = '-'
        if 'project' in order_by:
            order_by = direction + order_by
        elif 'resources' in order_by:
            split = order_by.split('__') # TODO - remove
            order_by = '__'.join(split) # TODO - remove
            order_by = direction + order_by
        else:
            order_by = direction + order_by.split('__')[1]
    else:
        order_by = 'project__id'
    allocations = Allocation.objects.prefetch_related('project', 'status',).all().order_by(order_by)

    if data.get('allocation__status__name'):
        allocations = allocations.filter(
            status__in=data.get('allocation__status__name')
        )

    return allocations

def build_resource_queryset(data):
    resources = Resource.objects.prefetch_related('resource_type',).filter(is_allocatable=True)

    if data.get('resources__name'):
        resources = resources.filter(
            id__in=data.get('resources__name').values_list('id')
        )
    if data.get('resources__resource_type__name'):
        print(data.get('resources__resource_type__name'))
        resources = resources.filter(
            resource_type__in=data.get('resources__resource_type__name')
        )

    return resources
    
def build_project_queryset(data, request):
    order_by = 'id'
    if data.get('only_search_projects'):
        order_by = request.get('order_by')
        if order_by:
            direction = request.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'

            split = order_by.split('__')[1:]
            order_by = '__'.join(split)
            order_by = direction + order_by
        else:
            order_by = 'id'

    projects = Project.objects.prefetch_related(
        'pi',
        'status',
        'type'
    ).all().order_by(order_by)

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

    return projects

def build_project_columns(data):
    columns = []
    for key, value in data.items():
        if 'display' in key and 'project' in key and value:
            display_name = ' '.join(key.split('_')[1:])
            field_name = key[len('display') + 2:]
            enable_sorting = 'false'
            if 'title' in field_name or 'description' in field_name:
                enable_sorting = 'false'
            columns.append({
                'enable_sorting': enable_sorting,
                'display_name': display_name.title(),
                'field_name': field_name
            })

    return columns

def build_project_rows(columns, queryset):
    column_field_names = [column.get('field_name') for column in columns]
    rows_dict = {}
    for i, result in enumerate(queryset):
        rows_dict[i] = []

        for column in column_field_names:
            split = column.split('__')[1:]
            nested_attribute = ""
            if len(split) == 2:
                attribute, nested_attribute = split
            else:
                attribute = split[0]

            attribute = getattr(result, attribute)
            if nested_attribute:
                attribute = getattr(attribute, nested_attribute)

            rows_dict[i].append(attribute)

    return rows_dict
