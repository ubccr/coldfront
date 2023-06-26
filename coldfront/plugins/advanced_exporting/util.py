from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeUsage
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
    additional_usage_data = get_allocation_attribute_usage(additional_data)
    rows = build_rows(columns, queryset, additional_data, additional_usage_data)

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

            has_usage = int(entry.get('allocationattribute__has_usage'))
            if has_usage and int(has_usage):
                display_name = key.name + ' Usage'
                field_name = 'allocationattribute__has_usage'
                enable_sorting = 'false'
                columns.append({
                    'enable_sorting': enable_sorting,
                    'display_name': display_name,
                    'field_name': field_name,
                    'id': key.id
                })

    return columns

def build_rows(columns, queryset, additional_data, additional_usage_data):
    rows_dict = {}
    for i, result in enumerate(queryset):
        rows_dict[i] = []

        for column in columns:
            field_name = column.get('field_name')
            if 'allocationattribute__name' in field_name:
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
            elif 'allocationattribute__has_usage' in field_name:
                allocation_id = result.id
                allocation_attribute_usages = additional_usage_data.get(allocation_id)
                if allocation_attribute_usages is not None:
                    value = ''
                    for allocation_attribute_usage in allocation_attribute_usages:
                        if allocation_attribute_usage.allocation_attribute.allocation_attribute_type.id == column.get('id'):
                            value = allocation_attribute_usage.value
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
        allocation_attribute_has_usage = entry.get('allocationattribute__has_usage')
        if allocation_attribute_has_usage is not None:
            allocation_attribute_has_usage = int(entry.get('allocationattribute__has_usage'))
        allocation_attribute_usage = entry.get('allocationattribute__usage')
        allocation_attribute_equality = entry.get('allocationattribute__equality')
        allocation_attribute_usage_format = entry.get('allocationattribute__usage__format')

        if allocation_attribute_type and allocation_attribute_value:
            allocation_queryset = allocation_queryset.filter(
                allocationattribute__allocation_attribute_type=allocation_attribute_type,
                allocationattribute__value__icontains=allocation_attribute_value
            )

        if allocation_attribute_type and allocation_attribute_has_usage and allocation_attribute_usage:
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
    all_allocation_attributes = {}
    for entry in data:
        allocation_attribute_type = entry.get('allocationattribute__name')
        if allocation_attribute_type:
            allocation_attributes = AllocationAttribute.objects.filter(
                allocation_attribute_type=allocation_attribute_type
            )
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
    all_allocation_attribute_usages = {}
    allocation_attributes = [
        allocation_attribute 
        for allocation_attributes in data.values() 
        for allocation_attribute in allocation_attributes
    ]
    allocation_attribute_usages = AllocationAttributeUsage.objects.filter(
        allocation_attribute__in=allocation_attributes
    )
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
